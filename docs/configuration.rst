Configuration
=============

The first time you invoke the tool, it will create a default configuration file and exit with a message telling you to edit the file. The file is created at the user config directory reported by ``platformdirs`` for the application name ``sobe``.

Location
--------

Typically the path looks like:

* Linux: ``~/.config/sobe/config.toml``
* macOS: ``~/Library/Application Support/sobe/config.toml``
* Windows: ``%APPDATA%\\sobe\\config.toml``

Template
--------

Here's a minimal configuration template:

.. code-block:: toml

   # sobe configuration

   url = "https://example.com/"

   [aws]
   bucket = "example-bucket"
   cloudfront = "E1111111111111"

   [aws.session]
   # If you already have AWS CLI set up, don't fill keys here.
   # region_name = "..."
   # profile_name = "..."
   # aws_access_key_id = "..."
   # aws_secret_access_key = "..."

   [aws.service]
   # verify = true

Editing Guidance
----------------

* ``url``: The public base URL for your uploads.
* ``aws.bucket``: Your target S3 bucket name.
* ``aws.cloudfront``: Distribution ID used for full-path invalidations.
* ``aws.session``: Dictionary of values passed to :class:`boto3.session.Session`.

  * You can put credentials and region here.
  * If you already have AWS CLI config set up with these settings, you can leave this empty.
  * Here's the documentation of all possible parameters: :class:`boto3.session.Session`

* ``aws.service``: Dictionary of extra options passed to each client/resource creation.

  * ``verify``: Controls SSL/TLS certificate verification. Set to ``false`` to disable certificate validation (useful for corporate MITM proxies or self-signed certificates, but not recommended for general use). Defaults to ``true`` (secure).

Once edited, re-run the command. If the bucket still matches the placeholder name the tool will recreate/overwrite the template and exit again.
