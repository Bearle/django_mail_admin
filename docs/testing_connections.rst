Testing Email Connections
========================

Django Mail Admin now provides methods to test both Mailbox (incoming) and Outbox (outgoing) connections using the credentials already configured on the model instances.

Testing Connections Programmatically
-----------------------------------

You can test connections directly in your Python code:

.. code-block:: python

    from django_mail_admin.models import Mailbox, Outbox

    # Test a specific mailbox
    mailbox = Mailbox.objects.get(id=1)
    success, message = mailbox.test_connection()
    if success:
        print(f"Connection successful: {message}")
    else:
        print(f"Connection failed: {message}")

    # Test a specific outbox
    outbox = Outbox.objects.get(id=1)
    success, message = outbox.test_connection()
    if success:
        print(f"Connection successful: {message}")
    else:
        print(f"Connection failed: {message}")

Using the Management Command
---------------------------

Django Mail Admin provides a management command to test connections from the command line:

.. code-block:: bash

    # Test a specific mailbox by ID
    python manage.py test_connections --mailbox=1

    # Test a specific outbox by ID
    python manage.py test_connections --outbox=1

    # Test all mailboxes and outboxes
    python manage.py test_connections --all

Using the Example Script
----------------------

An example script is provided in the `example` directory that demonstrates how to test connections:

.. code-block:: bash

    # Test a specific mailbox by ID
    python example/test_connections.py --mailbox=1

    # Test a specific outbox by ID
    python example/test_connections.py --outbox=1

    # Test all mailboxes and outboxes
    python example/test_connections.py --all

How It Works
-----------

Mailbox Connection Testing
~~~~~~~~~~~~~~~~~~~~~~~~~

The `test_connection()` method on the Mailbox model:

1. Attempts to establish a connection using the configured credentials
2. Tests the connection based on the transport type (IMAP, POP3, Office365, etc.)
3. Returns a tuple of (success, message) where:
   - `success` is a boolean indicating if the connection was successful
   - `message` contains details about the connection attempt

Outbox Connection Testing
~~~~~~~~~~~~~~~~~~~~~~~

The `test_connection()` method on the Outbox model:

1. Creates a backend alias based on the email host type (SMTP, Office365, Gmail)
2. Gets a connection using the ConnectionHandler
3. Tests the connection based on the backend type
4. Returns a tuple of (success, message) where:
   - `success` is a boolean indicating if the connection was successful
   - `message` contains details about the connection attempt

Supported Connection Types
-------------------------

The test_connection methods support various connection types:

For Mailbox:
- IMAP
- POP3
- Gmail (IMAP)
- Office365
- Local file transports (maildir, mbox, babyl, mh, mmdf)

For Outbox:
- SMTP
- Office365
- Gmail

Error Handling
------------

The test_connection methods include robust error handling to catch various connection issues. If a connection fails, the error message will be returned in the message part of the result tuple.
