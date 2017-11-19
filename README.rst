=============================
django mail admin
=============================

.. image:: https://badge.fury.io/py/django_mail_admin.svg
    :target: https://badge.fury.io/py/django_mail_admin

.. image:: https://travis-ci.org/delneg/django_mail_admin.svg?branch=master
    :target: https://travis-ci.org/delneg/django_mail_admin

.. image:: https://codecov.io/gh/delneg/django_mail_admin/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/delneg/django_mail_admin

The one and only django app to receive & send mail with templates and multiple configurations.



=================
Work In progress!
=================


Documentation
-------------

The full documentation is at https://django_mail_admin.readthedocs.io.

Quickstart
----------

Install django mail admin::

    pip install django_mail_admin

Add it to your `INSTALLED_APPS`:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'django_mail_admin',
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

Features
--------

* TODO

Running Tests
-------------

Does the code actually work?

::

    source <YOURVIRTUALENV>/bin/activate
    (myenv) $ pip install tox
    (myenv) $ tox

Credits
-------

Tools used in rendering this package:

*  Cookiecutter_
*  `cookiecutter-djangopackage`_

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`cookiecutter-djangopackage`: https://github.com/pydanny/cookiecutter-djangopackage
