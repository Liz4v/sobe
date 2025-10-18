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

Default template contents:

.. code-block:: toml

   # sobe configuration

   url = "https://example.com/"

   [aws]
   bucket = "example-bucket"
   cloudfront = "E1111111111111"

   [aws.session]
   # region_name = "..."
   # profile_name = "..."
   # aws_access_key_id = "..."
   # aws_secret_access_key = "..."

   [aws.service]
   verify = true

Editing Guidance
----------------

* ``url``: The public base URL for your uploads.
* ``aws.bucket``: Your target S3 bucket name.
* ``aws.cloudfront``: Distribution ID used for full-path invalidations.
* ``aws.session``: Values passed to ``boto3.Session`` (often you can leave this empty if you have AWS CLI config set up).
* ``aws.service``: Extra options passed to each client/resource creation (e.g. ``verify = true`` to enforce TLS certificate verification).

Once edited, re-run the command. If the bucket still matches the placeholder name the tool will recreate/overwrite the template and exit again.
