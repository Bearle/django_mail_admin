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


Optional requirements
---------------------

1. `django_admin_row_actions` for some useful actions in the admin interface
2. `requests` & social_django for Gmail


FAQ
---

**Q**: Why did you write this?

**A**: In order to get both email sending & receiving you'll have to install post_office AND django_mailbox.
Even if you do, you'll have to work on admin interface for it to look prettier, somehow link replies properly etc.
So I've decided merging those two and clearing the mess in between them as well as adding some other useful features.

**Q**: Why did you remove support for Python 2?

**A**: Because f*ck python2. Really, it's been 9 (NINE!) years since it came out. Go ahead and check out https://github.com/brettcannon/caniusepython3

**Q**: Why did you delete support for multi-lingual templates?

**A**: Well, we have django-model-translations for that. You can easily fork this app and override EmailTemplate model (models/templates.py) accordingly.
I think there's no need for such an overhead in a mail-related app.

**Q**: I don't want my outgoing emails to be queued for sending after saving them in the admin interface, what do i do?

**A**: Just override OutgoingEmailAdmin's save_model method.

**Q**: Can i get in touch with you? I want a new feature to be implemented/bug fixed!

**A**: Feel free to reach me out using issues and pull requests, I'll review them all and answer when I can.

**Q**: Why is it named django_mail_admin, what does it have to do with admin ?

**A**: Well, the first version of this package (which was living just in a really large admin.py) was used for easy mail management using standard Django admin interface.


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
