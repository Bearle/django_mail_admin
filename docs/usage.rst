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

Template variables & tags
-------------------------


``Django mail admin`` supports Django's template tags and variables.
It is important to note, however, that due to usage of TemplateVariable db-model,
only strings can be stored as value, and anything in the template will be treated as a string.

For example, ``'foo': [5,6]`` when called in template as ``{{ foo|first }}`` will result in ``[``,
not in ``5``. Please keep this in mind.

As an example of usage, if you put "Hello, {{ name }}" in the subject line and pass in
``{'name': 'Alice'}`` as variable_dict, you will get "Hello, Alice" as subject:

.. code-block:: python

    from post_office import mail, models

    models.EmailTemplate.objects.create(
        name='morning_greeting',
        subject='Morning, {{ name|capfirst }}',
        content='Hi {{ name }}, how are you feeling today?',
        html_content='Hi <strong>{{ name }}</strong>, how are you feeling today?',
    )

    mail.send(
        'from@example.com',
        'recipient@example.com', # List of email addresses also accepted
        template=template,
        priority=models.PRIORITY.now,
        variable_dict={'name': 'alice'})
    )

    # This will create an email with the following content:
    subject = 'Morning, Alice',
    content = 'Hi alice, how are you feeling today?'
    content = 'Hi <strong>alice</strong>, how are you feeling today?'

mail.send()
-----------

``mail.send`` is the most important function in this library, it takes these
arguments:

+--------------------+----------+--------------------------------------------------+
| Argument           | Required | Description                                      |
+--------------------+----------+--------------------------------------------------+
| recipients         | No       | list of recipient email addresses                |
+--------------------+----------+--------------------------------------------------+
| sender             | Yes      | Defaults to ``settings.DEFAULT_FROM_EMAIL``,     |
|                    |          | display name is allowed (``John <john@a.com>``)  |
+--------------------+----------+--------------------------------------------------+
| subject            | No       | Email subject (if ``template`` is not specified) |
+--------------------+----------+--------------------------------------------------+
| message            | No       | Email content (if ``template`` is not specified) |
+--------------------+----------+--------------------------------------------------+
| html_message       | No       | HTML content (if ``template`` is not specified)  |
+--------------------+----------+--------------------------------------------------+
| template           | No       | ``EmailTemplate`` instance                       |
+--------------------+----------+--------------------------------------------------+
| cc                 | No       | list emails, will appear in ``cc`` field         |
+--------------------+----------+--------------------------------------------------+
| bcc                | No       | list of emails, will appear in `bcc` field       |
+--------------------+----------+--------------------------------------------------+
| attachments        | No       | Email attachments - A dictionary where the keys  |
|                    |          | are the filenames and the values are either:     |
|                    |          |                                                  |
|                    |          | * files                                          |
|                    |          | * file-like objects                              |
|                    |          | * full path of the file                          |
+--------------------+----------+--------------------------------------------------+
| variables_dict     | No       | A dictionary, used to render templated email     |
+--------------------+----------+--------------------------------------------------+
| headers            | No       | A dictionary of extra headers on the message     |
+--------------------+----------+--------------------------------------------------+
| scheduled_time     | No       | A date/datetime object indicating when the email |
|                    |          | should be sent                                   |
+--------------------+----------+--------------------------------------------------+
| priority           | No       | ``high``, ``medium``, ``low`` or ``now``         |
|                    |          | (send_immediately)                               |
+--------------------+----------+--------------------------------------------------+
| backend            | No       | Alias of the backend you want to use.            |
|                    |          | ``default`` will be used if not specified.       |
+--------------------+----------+--------------------------------------------------+


Here are a few examples.

If you just want to send out emails without using database templates. You can
call the ``send`` command without the ``template`` argument.

.. code-block:: python

    from django_mail_admin import mail

    mail.send(
        'from@example.com',
        ['recipient1@example.com'],
        subject='Welcome!',
        message='Welcome home, {{ name }}!',
        html_message='Welcome home, <b>{{ name }}</b>!',
        headers={'Reply-to': 'reply@example.com'},
        scheduled_time=date(2019, 1, 1),
        variables_dict={'name': 'Alice'},
    )

``django_mail_admin`` is also task queue friendly. Passing ``now`` as priority into
``send_mail`` will deliver the email right away (instead of queuing it),
regardless of how many emails you have in your queue:

.. code-block:: python

    from django_mail_admin import mail, models

    mail.send(
        'from@example.com',
        ['recipient1@example.com'],
        template=models.EmailTemplate.objects.get(name='welcome'),
        variables_dict={'foo': 'bar'},
        priority='now',
    )

This is useful if you already use something like `django-rq <https://github.com/ui/django-rq>`_
to send emails asynchronously and only need to store email related activities and logs.

If you want to send an email with attachments:

.. code-block:: python

    from django.core.files.base import ContentFile
     from django_mail_admin import mail, models

    mail.send(
        ['recipient1@example.com'],
        'from@example.com',
        template=models.EmailTemplate.objects.get(name='welcome'),
        variables_dict={'foo': 'bar'},
        priority='now',
        attachments={
            'attachment1.doc': '/path/to/file/file1.doc',
            'attachment2.txt': ContentFile('file content'),
            'attachment3.txt': { 'file': ContentFile('file content'), 'mimetype': 'text/plain'},
        }
    )

send_many()
-----------

``send_many()`` is much more performant (generates less database queries) when
sending a large number of emails. ``send_many()`` is almost identical to ``mail.send()``,
with the exception that it accepts a list of keyword arguments that you'd
usually pass into ``mail.send()``:

.. code-block:: python

    from from django_mail_admin import mail

    first_email = {
        'sender': 'from@example.com',
        'recipients': ['alice@example.com'],
        'subject': 'Hi!',
        'message': 'Hi Alice!'
    }
    second_email = {
        'sender': 'from@example.com',
        'recipients': ['bob@example.com'],
        'subject': 'Hi!',
        'message': 'Hi Bob!'
    }
    kwargs_list = [first_email, second_email]

    mail.send_many(kwargs_list)

Attachments are not supported with ``mail.send_many()``.

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
