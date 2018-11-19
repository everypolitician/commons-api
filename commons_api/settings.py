import os
import re

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEBUG = bool(os.environ.get('DJANGO_DEBUG'))
USE_TZ = True

TIME_ZONE = 'Europe/London'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split() if not DEBUG else ['*']

SECRET_KEY = os.environ.get('SECRET_KEY', '')
if not SECRET_KEY and DEBUG:
    SECRET_KEY = 'very secret key'

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ.get('DATABASE_NAME', 'commons-api'),
    },
}

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'django.contrib.humanize',
    'rest_framework',
    'commons_api',
    'commons_api.proto_commons',
    'commons_api.wikidata',
]

try:
    __import__('django_extensions')
except ImportError:
    pass
else:
    INSTALLED_APPS.append('django_extensions')

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'reversion.middleware.RevisionMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.locale.LocaleMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': (
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.static',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
            ),
        },
    },
]


ROOT_URLCONF = 'commons_api.urls'
STATIC_URL = '/static/'

WDQS_URL = 'https://query.wikidata.org/sparql'

ENABLE_MODERATION = bool(os.environ.get('ENABLE_MODERATION'))

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 1000
}

DEMOCRATIC_COMMONS_GITHUB_USER = os.environ.get('DEMOCRATIC_COMMONS_GITHUB_USER', 'everypolitician')

if 'DYNO' in os.environ:
    # django_heroku uses dj_database_url, so tell it we're using PostGIS
    os.environ['DATABASE_URL'] = re.sub('^postgres:', 'postgis:', os.environ['DATABASE_URL'])

    # Configure Django App for Heroku.
    import django_heroku
    django_heroku.settings(locals())

    CELERY_BROKER_URL = os.environ.get('CLOUDAMQP_URL')
