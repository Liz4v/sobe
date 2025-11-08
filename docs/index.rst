.. sobe documentation master file

Welcome to sobe's documentation!
================================

A simple command-line tool to upload files to an AWS S3 bucket that is publicly available through a CloudFront distribution. This is the traditional "drop box" use case that existed long before the advent of modern file sharing services.

It will upload any files you give it to your bucket, defaulting to a current year directory, because that's the only easy way to organize chaos.

"Sobe" is Portuguese for "take it up" (in the imperative), as in "upload".

Contents:

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   usage
   configuration

.. toctree::
   :maxdepth: 2
   :caption: Reference

   api/cli
   api/config
   api/aws

Indices and tables
==================

* :ref:`modindex`
* :ref:`search`
