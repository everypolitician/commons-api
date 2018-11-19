__all__ = ['update_all_boundaries', 'update_boundaries_for_country']

import logging
from typing import Iterable

import celery
import github
import github.Consts
import github.PaginatedList
import github.Repository
from django.conf import settings

from .. import models

logger = logging.getLogger(__name__)


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
            country = models.Country.objects.get(iso_3166_1_code=iso_3166_1_code)
        except models.Country.DoesNotExist:
            logger.warning("Couldn't find Country with code %s for repo %s", iso_3166_1_code, repo.full_name)
            continue

        update_boundaries_for_country.delay(country.id, repo.full_name)


@celery.shared_task
def update_boundaries_for_country(country_id: str, repo_full_name: str=None):
    country = models.Country.objects.get(id=country_id)
    g = github.Github()
    if repo_full_name:
        github_repo = g.get_repo(repo_full_name)
    else:
        github_repo = get_github_repo_for_country(country)

    # TODO: Crawl and import boundaries


def get_github_repo_for_country(country: models.Country) -> github.Repository.Repository:
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