import datetime
import http.client
import json
import os
import resource
import shutil
import tempfile
from ctypes import c_void_p
from pathlib import Path

import requests
from django.contrib.gis.gdal.libgdal import lgdal
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.gdal.prototypes.generation import void_output, int_output
from django.db import transaction

from boundaries.management.commands.loadshapefiles import Command as LoadShapefilesCommand, create_data_sources
from boundaries.models import Definition, BoundarySet
from commons_api.proto_commons.models import Shapefile
from commons_api.wikidata.models import Country, Spatial


__all__ = ['update_all_boundaries', 'update_boundaries_for_country']

import logging
from typing import Iterable

import celery
import github
import github.Consts
import github.PaginatedList
import github.Repository

from django.apps import apps
from django.conf import settings
from django.contrib.gis.gdal.prototypes import ds as capi

logger = logging.getLogger(__name__)

SHAPEFILE_EXTENSIONS = ('.shp', '.shx', '.dbf', '.prj', '.cpg', '.qpj', '-COPYRIGHT')

flatten_to_2d = void_output(lgdal.OGR_G_FlattenTo2D, [c_void_p])
try:  # GDAL 2.1+
    coordinate_dimension = int_output(lgdal.OGR_G_CoordinateDimension, [c_void_p])
except AttributeError:  # GDAL 1.10
    coordinate_dimension = int_output(lgdal.OGR_G_GetCoordinateDimension, [c_void_p])


@celery.shared_task
def update_all_boundaries():
    for repo in get_github_repos_with_topics():  # type: github.Repository.Repository
        if 'commons-data' not in repo.topics:
            continue

        for topic in repo.topics:
            if topic.startswith('country-code-'):
                iso_3166_1_code = topic[len('country-code-'):].upper()
                break
        else:
            continue

        try:
            country = Country.objects.get(iso_3166_1_code=iso_3166_1_code)
        except Country.DoesNotExist:
            logger.warning("Couldn't find Country with code %s for repo %s", iso_3166_1_code, repo.full_name)
            continue

        update_boundaries_for_country.delay(country.id, repo.full_name)


@celery.shared_task
def update_boundaries_for_country(country_id: str, repo_full_name: str=None):
    country = Country.objects.get(id=country_id)
    g = github.Github()
    if repo_full_name:
        github_repo = g.get_repo(repo_full_name)
    else:
        github_repo = get_github_repo_for_country(country)

    try:
        boundaries_url = 'https://raw.githubusercontent.com/{repo_full_name}/master/boundaries/build/'.format(
            repo_full_name=github_repo.full_name
        )
        response = requests.get(boundaries_url + 'index.json')
        response.raise_for_status()
    except requests.HTTPError:
        boundaries_url = 'https://raw.githubusercontent.com/{repo_full_name}/master/boundaries/'.format(
            repo_full_name=github_repo.full_name
        )
        response = requests.get(boundaries_url + 'index.json')
        response.raise_for_status()

    boundaries_index = response.json()
    directories = {entry['directory'] for entry in boundaries_index}
    for directory in directories:
        update_boundaries.delay(country_id, '{}{}/{}.shp'.format(boundaries_url, directory, directory))


@celery.shared_task
def update_boundaries(country_id: str, shapefile_url: str):
    shapefile, _ = Shapefile.objects.get_or_create(url=shapefile_url)
    _, etags = download_shapefile(country_id, shapefile_url, head=True)
    if shapefile.etags != etags:
        import_shapefile.delay(country_id, shapefile_url)


@celery.shared_task
@transaction.atomic
def import_shapefile(country_id: str, shapefile_url: str):
    slug = shapefile_url.rsplit('/', 1)[-1].split('.')[0]
    print(f"Importing {shapefile_url}")
    country = Country.objects.get(id=country_id)
    shapefile_path, etags = download_shapefile(country_id, shapefile_url)
    try:
        source_notes = Path(shapefile_path[:-4] + '-COPYRIGHT').read_text()
    except FileNotFoundError:
        source_notes = ''
    try:
        # Update the ETags
        shapefile, _ = Shapefile.objects.select_for_update().get_or_create(url=shapefile_url)
        if shapefile.etags == etags:
            return

        load_shapefiles_command = LoadShapefilesCommand()
        options = {'merge': None, 'clean': False}
        definition = Definition({'file': shapefile_path,
                                 'name': '{} boundaries for {} ({})'.format(slug, country.label, country.id),
                                 'singular': 'boundary',
                                 'encoding': 'utf-8',
                                 'last_updated': datetime.datetime.now(),
                                 'name_func': lambda feature: feature.get('WIKIDATA'),
                                 'id_func': lambda feature: feature.get('WIKIDATA'),
                                 'notes': source_notes})

        data_sources, tmpdirs = create_data_sources(definition['file'], encoding=definition['encoding'],
                                                    convert_3d_to_2d=options['clean'])

        flatten_data_sources(data_sources)

        load_shapefiles_command.load_boundary_set(slug=country_id + '-' + slug,
                                                  definition=definition,
                                                  data_sources=data_sources,
                                                  options=options)

        # Update the ETags
        shapefile.etags = etags
        shapefile.save()

        print("Done: {}".format(sizeof_fmt(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)))

        boundary_set = BoundarySet.objects.get(slug=country_id + '-' + slug)
        update_wikidata_boundary_links(boundary_set)
    finally:
        # Always clear up the download directory
        shutil.rmtree(os.path.dirname(shapefile_path))


def get_spatial_model(app_label, model):
    ct = ContentType.objects.get_by_natural_key(app_label, model)
    model = ct.model_class()
    if not issubclass(model, Spatial):
        raise TypeError('Model {} with content_type {}.{} is not a subclass of the Spatial model'.format(model, app_label, model))
    return model


def flatten_data_sources(data_sources):
    """Iterates through data_sources, ensuring all geometries are 2D, for loading into PostGIS"""
    for data_source in data_sources:
        for layer in data_source:
            for feature in layer:
                geom_ptr = capi.get_feat_geom_ref(feature.ptr)
                if coordinate_dimension(geom_ptr) > 2:
                    flatten_to_2d(geom_ptr)


def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def download_shapefile(country_id: str, shapefile_url: str, head: bool=False):
    """Downloads a shapefile from the web, and returns the file path

    This also uses ETags to ensure that we don't unnecessarily redownload files that haven't changed.
    """
    if not head:
        download_directory = tempfile.mkdtemp()
    else:
        download_directory = None

    try:
        etags = {}
        for ext in SHAPEFILE_EXTENSIONS:
            filename = shapefile_url.rsplit('/', 1)[-1].rsplit('.', 1)[0] + ext
            response = requests.request('HEAD' if head else 'GET',
                                        shapefile_url.rsplit('.', 1)[0] + ext,
                                        stream=True)
            if response.status_code == http.client.OK:
                etags[filename] = response.headers['ETag']
                if not head:
                    filepath = os.path.join(download_directory, filename)
                    with open(filepath, 'wb') as f:
                        response.raw.decode_content = True
                        shutil.copyfileobj(response.raw, f)

        if head:
            return None, etags
        else:
            return os.path.join(download_directory, shapefile_url.rsplit('/', 1)[-1]), etags
    except BaseException:
        if download_directory:
            # If the full download failed for any reason, clean up any other files
            shutil.rmtree(download_directory)
        raise


def get_github_repo_for_country(country: Country) -> github.Repository.Repository:
    """Return a Democratic Commons repository for a given country

    If no repository could be found, or the Country object doesn't have an ISO 3166-1 code, this raises ValueError

    :param country: The Country object for which to find a country
    :return: The associated Repository
    """
    if not country.iso_3166_1_code:
        raise ValueError("Country {} ({}) has no ISO 3166-1 code".format(country.id, country.label))
    for repo in get_github_repos_with_topics():
        if {'commons-data', 'country-code-' + country.iso_3166_1_code.lower()}.issubset(set(repo.topics)):
            return repo
    else:
        raise ValueError("Couldn't find repo for country {} ({})".format(country.id, country.label))


def get_github_repos_with_topics() -> Iterable[github.Repository.Repository]:
    """Return all repositories for the Democratic Commons GitHub user, with topics pre-populated

    :return: An iterable of Repository objects
    """
    g = github.Github()
    github_user = g.get_user(settings.DEMOCRATIC_COMMONS_GITHUB_USER)
    # We don't use `github_user.get_repos()` because it doesn't use the "mercy" preview
    # (https://developer.github.com/v3/repos/) to return topics in the results. Without this, we'd be making API calls
    # per repository to fetch topics.
    return github.PaginatedList.PaginatedList(
        github.Repository.Repository,
        github_user._requester,  # pylint: disable=W0212
        github_user.url + "/repos",
        firstParams={},
        headers={
            'Accept': github.Consts.mediaTypeTopicsPreview,
        }
    )


def update_wikidata_boundary_links(boundary_set: BoundarySet):
    id_mapping = dict(boundary_set.boundaries.values_list('external_id', 'pk'))
    for model in apps.get_models():
        if issubclass(model, Spatial):
            for obj in model.objects.filter(id__in=id_mapping):
                obj.boundary_id = id_mapping[obj.id]
                obj.save(force_update=True)


