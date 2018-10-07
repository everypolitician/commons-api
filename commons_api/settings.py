import os


DEBUG = bool(os.environ.get('DJANGO_DEBUG'))
USE_TZ = True

TIME_ZONE = 'Europe/London'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split() if not DEBUG else ['*']

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if not SECRET_KEY and DEBUG:
    SECRET_KEY = 'very secret key'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
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
            ),
        },
    },
]


ROOT_URLCONF = 'commons_api.urls'
STATIC_URL = '/static/'

WDQS_URL = 'https://query.wikidata.org/sparql'

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 1000
}