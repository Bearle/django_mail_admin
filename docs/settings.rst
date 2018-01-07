========
Settings
========

You should specify settings in your settings.py like this::

    DJANGO_MAIL_ADMIN = {
            'BATCH_SIZE': 1000,
            'LOG_LEVEL': 1,
        }

Here's a list of available settings:

Settings for outgoing email
---------------------------

+-----------------------+----------------------------------------------------------------------------------------------------+---------------+
| Setting               | Description                                                                                        | Default       |
+=======================+====================================================================================================+===============+
| BATCH_SIZE            | How many email's to send at a time. Used in `mail.py/get_queued`                                   | 100           |
+-----------------------+----------------------------------------------------------------------------------------------------+---------------+
| THREADS_PER_PROCESS   | How many threads to use when sending emails                                                        | 5             |
+-----------------------+----------------------------------------------------------------------------------------------------+---------------+
| DEFAULT_PRIORITY      | Priority, which is assigned to new email if not given specifically                                 | 'medium'      |
+-----------------------+----------------------------------------------------------------------------------------------------+---------------+
| LOG_LEVEL             | Log level. 0 - log nothing, 1 - log errors, 2 - log errors and successors                          | 2             |
+-----------------------+----------------------------------------------------------------------------------------------------+---------------+
| SENDING_ORDER         | Sending order for emails. If you want to send queued emails in FIFO order, set this to ['created'] | ['-priority'] |
+-----------------------+----------------------------------------------------------------------------------------------------+---------------+

Settings for incoming email
---------------------------

6. *STRIP_UNALLOWED_MIMETYPES*
7. *TEXT_STORED_MIMETYPES*
8. *ALTERED_MESSAGE_HEADER*
9. *ATTACHMENT_INTERPOLATION_HEADER*
10. *ATTACHMENT_UPLOAD_TO*
11. *STORE_ORIGINAL_MESSAGE*
12. *COMPRESS_ORIGINAL_MESSAGE*
13. *ORIGINAL_MESSAGE_COMPRESSION*
14. *DEFAULT_CHARSET*
