Lanister
=============

Lanister is a Nexus switch manager, until something better comes along. It's
based on [weber-minimal](https://github.com/vmalloc/weber-minimal), the readme
of which has been included below.

Weber-Minimal
=============

![Build Status](https://secure.travis-ci.org/vmalloc/weber-minimal.png?branch=master ) 

weber-minimal is a Flask application template, intended to get you started with a Flask-powered webapp as quickly as possible. Unlike [weber-backend](https://github.com/vmalloc/weber-backend ), weber-minimal aims at a minimalistic app, with no database engine or other bells and whistles.

weber-minimal puts an emphasis on ease of deployment (with *ansible*), and not getting in your way while you focus on your actual app logic.

Getting Started
===============

1. Check out the repository
2. Go through the configuration in `flask_app/app.yml` - most configuration options there are self-explanatory, and you might be interested in tweaking them to your needs.
3. Make sure you have `virtualenv` installed
4. Run the test server to experiment:
```
$ python manage.py testserver
```

Using an alternative Python version
===================================
By default, weber looks for a Python executable named `python2.7`. This can be overridden by changing `_lib/bootstrapping.py`. For example, it can be set to `python3.4`.

If you use an alternative interpreter then remember to add it to `ansible/roles/common/vars/main.yml`.

Installation/Deployment
=======================

See `INSTALLING.md`

Development
===========

To start developing and testing, bootstrap the development environment with:

```
$ python manage.py bootstrap --develop
```

License
=======

Weber is distributed under the BSD 3-clause license.
