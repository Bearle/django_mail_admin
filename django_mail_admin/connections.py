from threading import local

from django.core.mail import get_connection

from .settings import get_backend


# Copied from Django 1.8's django.core.cache.CacheHandler
class ConnectionHandler(object):
    """
    A Cache Handler to manage access to Cache instances.

    Ensures only one instance of each alias exists per thread.
    """

    def __init__(self):
        self._connections = local()

    def __getitem__(self, maybe_hacked_alias):
        try:
            return self._connections.connections[maybe_hacked_alias]
        except AttributeError:
            self._connections.connections = {}
        except KeyError:
            pass

        # as a hack other places are using backend_alias;;;from_email. e.g. o365;;;email@example.com
        # previously it just used any outbox for the alias
        real_alias = maybe_hacked_alias
        from_email: str | None = None
        if ";;;" in maybe_hacked_alias:
            real_alias,from_email = maybe_hacked_alias.split(";;;")

        try:
            backend_class = get_backend(real_alias)
        except KeyError:
            raise KeyError('%s is not a valid backend alias' % real_alias)

        # backend_instance is a EmailBackend subclass like O365Backend or GmailOAuth2Backend
        backend_instance = get_connection(backend_class)

        # now mutate the backend class after init since get_connection is within django
        backend_instance.from_email = from_email

        backend_instance.open()
        self._connections.connections[maybe_hacked_alias] = backend_instance
        return backend_instance

    def all(self):
        return getattr(self._connections, 'connections', {}).values()

    def close(self):
        for connection in self.all():
            connection.close()


connections = ConnectionHandler()
