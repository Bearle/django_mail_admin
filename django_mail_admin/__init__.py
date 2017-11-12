__version__ = '0.1.0'
default_app_config = 'django_mail_admin.apps.DjangoMailAdminConfig'
from .mail import send, send_many
# TODO: add functions for receiving email
