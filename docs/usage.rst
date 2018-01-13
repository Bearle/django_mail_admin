=====
Usage
=====

After you've installed Django Mail Admin:


Send a simple email is really easy:

.. code-block:: python

    from django_mail_admin import mail, models

    mail.send(
        'from@example.com',
        'recipient@example.com', # List of email addresses also accepted
        subject='My email',
        message='Hi there!',
        priority=models.PRIORITY.now,
        html_message='Hi <strong>there</strong>!',
    )


If you want to use templates: create an
``EmailTemplate`` instance via ``admin`` or ``manually`` and do the following:

.. code-block:: python

    from post_office import mail, models

    template = models.EmailTemplate.objects.create(name='first', description='desc', subject='{{id}}',
                                                email_html_text='{{id}}')
    email = mail.create('from@example.com',
                        'recipient@example.com', # List of email addresses also accepted
                        template=template,
                        priority=models.PRIORITY.now)

    models.TemplateVariable.objects.create(name='id', value=1, email=email)
    models.OutgoingEmail.objects.get(id=email.id).dispatch() # re-get it from DB for template variable to kick in, not needed when sending emails from queue via cron/celery/etc.
    # OR
    mail.send('from@example.com',
              'recipient@example.com', # List of email addresses also accepted
               template=template,
               priority=models.PRIORITY.now,
               variable_dict={'id': 1})

Management Commands
-------------------

* ``send_queued_mail`` - send queued emails, those aren't successfully sent
  will be marked as ``failed``. Accepts the following arguments:

+---------------------------+--------------------------------------------------+
| Argument                  | Description                                      |
+---------------------------+--------------------------------------------------+
| ``--processes`` or ``-p`` | Number of parallel processes to send email.      |
|                           | Defaults to 1                                    |
+---------------------------+--------------------------------------------------+
| ``--lockfile`` or ``-L``  | Full path to file used as lock file. Defaults to |
|                           | ``/tmp/post_office.lock``                        |
+---------------------------+--------------------------------------------------+


* ``cleanup_mail`` - delete all emails created before an X number of days
  (defaults to 90).

+---------------------------+--------------------------------------------------+
| Argument                  | Description                                      |
+---------------------------+--------------------------------------------------+
| ``--days`` or ``-d``      | Number of days to filter by.                     |
+---------------------------+--------------------------------------------------+

* ``get_new_mail`` - receive new emails for all mailboxes or, if any args passed - filtered, e.g.:


.. code-block:: python

    python manage.py get_new_mail `test`


Set cron/Celery/RQ job to send/receive email, e.g. ::


    * * * * * (cd $PROJECT; python manage.py send_queued_mail --processes=1 >> $PROJECT/cron_mail.log 2>&1)
    * * * * * (cd $PROJECT; python manage.py get_new_mail >> $PROJECT/cron_mail_receive.log 2>&1)
    0 1 * * * (cd $PROJECT; python manage.py cleanup_mail --days=30 >> $PROJECT/cron_mail_cleanup.log 2>&1)


If you use uWSGI as application server, add this short snipped  to the
project's ``wsgi.py`` file:

.. code-block:: python

    from django.core.wsgi import get_wsgi_application

    application = get_wsgi_application()

    # add this block of code
    try:
        import uwsgidecorators
        from django.core.management import call_command

        @uwsgidecorators.timer(10)
        def send_queued_mail(num):
            """Send queued mail every 10 seconds"""
            call_command('send_queued_mail', processes=1)

    except ImportError:
        print("uwsgidecorators not found. Cron and timers are disabled")

Alternatively you can also use the decorator ``@uwsgidecorators.cron(minute, hour, day, month, weekday)``.
This will schedule a task at specific times. Use ``-1`` to signal any time, it corresponds to the uWSGI
in cron.

Please note that ``uwsgidecorators`` are available only, if the application has been started
with **uWSGI**. However, Django's internal ``./manage.py runserver`` also access this file,
therefore wrap the block into an exception handler as shown above.

This configuration is very useful in environments, such as Docker containers, where you
don't have a running cron-daemon.

Logging
-------

You can configure Django Mail Admin's logging from Django's settings.py. For example:

.. code-block:: python

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "django_mail_admin": {
                "format": "[%(levelname)s]%(asctime)s PID %(process)d: %(message)s",
                "datefmt": "%d-%m-%Y %H:%M:%S",
            },
        },
        "handlers": {
            "django_mail_admin": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "django_mail_admin"
            },
            # If you use sentry for logging
            'sentry': {
                'level': 'ERROR',
                'class': 'raven.contrib.django.handlers.SentryHandler',
            },
        },
        'loggers': {
            "django_mail_admin": {
                "handlers": ["django_mail_admin", "sentry"],
                "level": "INFO"
            },
        },
    }
