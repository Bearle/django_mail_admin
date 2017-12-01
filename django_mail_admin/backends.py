from django.core.mail.backends.smtp import EmailBackend
from .models import Outbox
import threading


class CustomEmailBackend(EmailBackend):
    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, use_ssl=None, timeout=None,
                 ssl_keyfile=None, ssl_certfile=None,
                 **kwargs):
        super(CustomEmailBackend, self).__init__(fail_silently=fail_silently)
        # TODO: implement choosing backend for a letter as a param
        configurations = Outbox.objects.filter(active=True)
        if len(configurations) > 1 or len(configurations) == 0:
            raise ValueError('Got %(l)s active configurations, expected 1' % {'l': len(configurations)})
        else:
            configuration = configurations.first()
        self.host = host or configuration.email_host
        self.port = port or configuration.email_port
        self.username = configuration.email_host_user if username is None else username
        self.password = configuration.email_host_password if password is None else password
        self.use_tls = configuration.email_use_tls if use_tls is None else use_tls
        self.use_ssl = configuration.email_use_ssl if use_ssl is None else use_ssl
        self.timeout = configuration.email_timeout if timeout is None else timeout
        self.ssl_keyfile = configuration.email_ssl_keyfile if ssl_keyfile is None else ssl_keyfile
        self.ssl_certfile = configuration.email_ssl_certfile if ssl_certfile is None else ssl_certfile
        self.connection = None
        self._lock = threading.RLock()
