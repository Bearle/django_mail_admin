import warnings

from django.conf import settings
from django.core.cache import caches
from django.core.cache.backends.base import InvalidCacheBackendError
from django.utils.translation import ugettext_lazy as _


def get_cache(name):
    return caches[name]


def get_backend(alias='default'):
    return get_available_backends()[alias]


def get_available_backends():
    """ Returns a dictionary of defined backend classes. For example:
    {
        'default': 'django.core.mail.backends.smtp.EmailBackend',
        'locmem': 'django.core.mail.backends.locmem.EmailBackend',
    }
    """
    backends = get_config().get('BACKENDS', {})

    if backends:
        return backends

    # Try to get backend settings from old style
    # DJANGO_MAIL_ADMIN = {
    #     'EMAIL_BACKEND': 'mybackend'
    # }
    backend = get_config().get('EMAIL_BACKEND')
    if backend:
        warnings.warn('Please use the new DJANGO_MAIL_ADMIN["BACKENDS"] settings',
                      DeprecationWarning)

        backends['default'] = backend
        return backends

    # Fall back to Django's EMAIL_BACKEND definition
    backends['default'] = getattr(
        settings, 'EMAIL_BACKEND',
        'django_mail_admin.backends.CustomEmailBackend')

    # TODO: review this code later
    # # If EMAIL_BACKEND is set to use PostOfficeBackend
    # # and DJANGO_MAIL_ADMIN_BACKEND is not set, fall back to SMTP
    # if 'django_mail_admin.EmailBackend' in backends['default']:
    #     backends['default'] = 'django.core.mail.backends.smtp.EmailBackend'

    return backends


def get_backend_names_str():
    return _('Available backends are: ') + str(list(get_available_backends().keys()))


def get_cache_backend():
    if hasattr(settings, 'CACHES'):
        if "django_mail_admin" in settings.CACHES:
            return get_cache("django_mail_admin")
        else:
            # Sometimes this raises InvalidCacheBackendError, which is ok too
            try:
                return get_cache("default")
            except InvalidCacheBackendError:
                pass
    return None


def get_config():
    """
    Returns Django Mail Admin's configuration in dictionary format. e.g:
    DJANGO_MAIL_ADMIN = {
        'BATCH_SIZE': 1000
    }
    """
    return getattr(settings, 'DJANGO_MAIL_ADMIN', {})


def get_batch_size():
    return get_config().get('BATCH_SIZE', 100)


def get_threads_per_process():
    return get_config().get('THREADS_PER_PROCESS', 5)


def get_default_priority():
    return get_config().get('DEFAULT_PRIORITY', 'medium')


def get_log_level():
    return get_config().get('LOG_LEVEL', 2)


def get_sending_order():
    return get_config().get('SENDING_ORDER', ['-priority'])


def strip_unallowed_mimetypes():
    return get_config().get('STRIP_UNALLOWED_MIMETYPES', False)


def get_allowed_mimetypes():
    return get_config().get('ALLOWED_MIMETYPES', ['text/plain', 'text/html'])


def get_text_stored_mimetypes():
    return get_config().get('TEXT_STORED_MIMETYPES', ['text/plain', 'text/html'])


def get_altered_message_header():
    return get_config().get('ALTERED_MESSAGE_HEADER', 'X-Django-Mail-Admin-Altered-Message')


def get_attachment_interpolation_header():
    return get_config().get('ATTACHMENT_INTERPOLATION_HEADER', 'X-Django-Mail-Admin-Interpolate-Attachment')


def get_attachment_upload_to():
    return get_config().get('ATTACHMENT_UPLOAD_TO', 'mail_admin_attachments/%Y/%m/%d/')


def get_store_original_message():
    return get_config().get('STORE_ORIGINAL_MESSAGE', True)


def get_compress_original_message():
    return get_config().get('COMPRESS_ORIGINAL_MESSAGE', False)


def get_original_message_compression():
    return get_config().get('ORIGINAL_MESSAGE_COMPRESSION', 6)


def get_default_charset():
    return get_config().get('DEFAULT_CHARSET', 'iso8859-1')
