=============================
Django Mail Admin
=============================

.. image:: https://badge.fury.io/py/django_mail_admin.svg
    :target: https://badge.fury.io/py/django_mail_admin

.. image:: https://travis-ci.org/Bearle/django_mail_admin.svg?branch=master
    :target: https://travis-ci.org/Bearle/django_mail_admin

.. image:: https://codecov.io/gh/delneg/django_mail_admin/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/delneg/django_mail_admin

The one and only django app to receive & send mail with templates and multiple configurations.


Screenshots
-----------

.. image:: https://github.com/Bearle/django_mail_admin/blob/master/screenshots/1.jpg?raw=true
.. image:: https://github.com/Bearle/django_mail_admin/blob/master/screenshots/2.jpg?raw=true

Features
--------

* Everything django-mailbox has
* Everything django-post-office has
* Everything django-db-email-backend has
* Database configurations - activate an outbox to send from, activate a mailbox to receive from
* Templates
* Translatable
* Mailings - using send_many() or 'cc' and 'bcc' or even recipients - all of those accept comma-separated lists of emails

Dependencies
============

* `django >= 1.9 <http://djangoproject.com/>`_
* `django-jsonfield <https://github.com/bradjasper/django-jsonfield>`_

Documentation
-------------

The full documentation is at https://django_mail_admin.readthedocs.io.

Quickstart
----------

**Q**: What versions of Django/Python are supported?
**A**: Take a look at https://travis-ci.org/delneg/django_mail_admin

Install django mail admin::

    pip install django_mail_admin

Add it to your `INSTALLED_APPS`:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'django_mail_admin',
        ...
    )

* Run ``migrate``::

    python manage.py migrate django_mail_admin

* Set ``django_mail_admin.backends.CustomEmailBackend`` as your ``EMAIL_BACKEND`` in django's ``settings.py``::

    EMAIL_BACKEND = 'django_mail_admin.backends.CustomEmailBackend'


* Set cron/Celery/RQ job to send/receive email, e.g. ::

    * * * * * (cd $PROJECT; python manage.py send_queued_mail --processes=1 >> $PROJECT/cron_mail.log 2>&1)
    * * * * * (cd $PROJECT; python manage.py get_new_mail >> $PROJECT/cron_mail_receive.log 2>&1)
    0 1 * * * (cd $PROJECT; python manage.py cleanup_mail --days=30 >> $PROJECT/cron_mail_cleanup.log 2>&1)

.. note::

   Once you have entered a mailbox to receive emails, you can easily verify that you
   have properly configured your mailbox by either:

   * From the Django Admin, using the 'Get New Mail' action from the action
     dropdown on the Mailbox changelist
   * *Or* from a shell opened to your project's directory, using the
     ``get_new_mail`` management command by running::

       python manage.py get_new_mail

   If you have also configured the Outbox, you can verify that it is working, e.g. ::

        from django_mail_admin import mail, models

        mail.send(
            'from@example.com',
            'recipient@example.com', # List of email addresses also accepted
            subject='My email',
            message='Hi there!',
            priority=models.PRIORITY.now,
            html_message='Hi <strong>there</strong>!',
        )

Custom Email Backends
---------------------

By default, ``django_mail_admin`` uses custom Email Backends that looks up for Outbox models in database. If you want to
use a different backend, you can do so by configuring ``BACKENDS``, though you will not be able to use Outboxes and will have to set EMAIL_HOST etc. in django's ``settings.py``.

For example if you want to use `django-ses <https://github.com/hmarr/django-ses>`_::

    DJANGO_MAIL_ADMIN = {
        'BACKENDS': {
            'default': 'django_mail_admin.backends.CustomEmailBackend',
            'smtp': 'django.core.mail.backends.smtp.EmailBackend',
            'ses': 'django_ses.SESBackend',
        }
    }

You can then choose what backend you want to use when sending mail:

.. code-block:: python

    # If you omit `backend_alias` argument, `default` will be used
    mail.send(
        'from@example.com',
        ['recipient@example.com'],
        subject='Hello',
    )

    # If you want to send using `ses` backend
    mail.send(
        'from@example.com',
        ['recipient@example.com'],
        subject='Hello',
        backend='ses',
    )

Capture outgoing emails into Outbox
-----------------------------------

If you want to store outgoing emails in the Outbox before they are submitted
to the backend, set ``django_mail_admin.backends.OutboxEmailBackend`` as your
``EMAIL_BACKEND`` in django's ``settings.py``::

    EMAIL_BACKEND='django_mail_admin.backends.OutboxEmailBackend'

Emails submitted using ``django.core.mail.send_mail`` will be stored in
the Outbox with the default backend selected for use when sending.

The emails will remain in the Outbox until ``send_queued_mail`` is run.

This can be used on development and test environments to capture emails
so they are not sent automatically, and can be reviewed in Django Admin
to ensure the contents are correct.

Optional requirements
---------------------

1. `django_admin_row_actions` for some useful actions in the admin interface
2. `requests` & `social-auth-app-django` for Gmail


FAQ
---

**Q**: Why did you write this?

**A**: In order to get both email sending & receiving you'll have to install post_office AND django_mailbox.
Even if you do, you'll have to work on admin interface for it to look prettier, somehow link replies properly etc.
So I've decided merging those two and clearing the mess in between them as well as adding some other useful features.

**Q**: Why did you remove support for Python 2?

**A**: Because f*ck python2. Really, it's been 9 (NINE!) years since it came out. Go ahead and check out https://github.com/brettcannon/caniusepython3

**Q**: Why is it named django_mail_admin, what does it have to do with admin ?

**A**: Well, the first version of this package (which was living just in a really large admin.py) was used for easy mail management using standard Django admin interface.

**Q**: What languages are available?

**A**: Currently there's Russian and English languages available. Feel free to add yours:

::

    source <YOURVIRTUALENV>/bin/activate
    python manage.py makemessages -l YOUR_LOCALE -i venv
    python manage.py compilemessages -l YOUR_LOCALE


**Q**: Why did you delete support for multi-lingual templates?

**A**: Well, we have django-model-translations for that. You can easily fork this app and override EmailTemplate model (models/templates.py) accordingly.
I think there's no need for such an overhead in a mail-related app.

**Q**: I don't want my outgoing emails to be queued for sending after saving them in the admin interface, what do i do?

**A**: Just override OutgoingEmailAdmin's save_model method.

**Q**: Can i get in touch with you? I want a new feature to be implemented/bug fixed!

**A**: Feel free to reach me out using issues and pull requests, I'll review them all and answer when I can.



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
