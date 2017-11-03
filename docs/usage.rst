=====
Usage
=====

To use django mail admin in a project, add it to your `INSTALLED_APPS`:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'django_mail_admin.apps.DjangoMailAdminConfig',
        ...
    )

Add django mail admin's URL patterns:

.. code-block:: python

    from django_mail_admin import urls as django_mail_admin_urls


    urlpatterns = [
        ...
        url(r'^', include(django_mail_admin_urls)),
        ...
    ]
