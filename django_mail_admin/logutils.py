import logging
from logging.config import dictConfig


# Taken from https://github.com/nvie/rq/blob/master/rq/logutils.py
def setup_loghandlers(level=None):
    # Setup logging for django_mail_admin if not already configured
    logger = logging.getLogger('django_mail_admin')
    if not logger.handlers:
        dictConfig({
            "version": 1,
            "disable_existing_loggers": False,

            "formatters": {
                "django_mail_admin": {
                    "format": "[%(levelname)s]%(asctime)s PID %(process)d: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },

            "handlers": {
                "django_mail_admin": {
                    "level": "DEBUG",
                    "class": "logging.StreamHandler",
                    "formatter": "django_mail_admin"
                },
            },

            "loggers": {
                "django_mail_admin": {
                    "handlers": ["django_mail_admin"],
                    "level": level or "DEBUG"
                }
            }
        })
    return logger
