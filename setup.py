#!/usr/bin/env python3
#
# This file is part of Superdesk.
#
# Copyright 2013-2020 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from setuptools import setup, find_packages

LONG_DESCRIPTION = "Superdesk Server Core"

install_requires = [
    "urllib3>=1.26,<3",
    "eve>=1.1.2,<=2.2.0",
    "eve-elastic>=7.4.0,<7.5.0",
    "elasticsearch<7.18",  # we are using oss version on test server
    "flask>=1.1,<1.2",
    "flask-mail>=0.9,<0.11",
    "flask-script>=2.0.5,<3.0",
    "flask-babel>=1.0,<4.1",
    "arrow>=0.4,<=1.3.0",
    "pillow>=9.2,<11.2",
    "bcrypt>=3.1.1,<4.3",
    "blinker>=1.3,<1.10",
    "celery[redis]>=5.2.7,<5.5",
    "cerberus>=1.3.2,<1.4",
    "redis>=4.5.2,<5.3",
    "kombu>=5.2.4,<5.5",
    "feedparser>=6.0.8,<6.1",
    "hachoir<=3.3.0",
    "HermesCache>=0.10.0,<1.1.0",
    "python-magic>=0.4,<0.5",
    "ldap3>=2.2.4,<2.10",
    "pytz>=2021.3",
    "tzlocal>=2.1,<3.0",
    "raven[flask]>=5.10,<7.0",
    "requests>=2.7.0,<3.0",
    "boto3>=1.26,<2.0",
    "websockets>=10.3,<13.2",
    "PyYAML>=6.0.1",
    "lxml>=5.2.2,<5.4",
    "lxml_html_clean>=0.1.1,<0.5",
    "python-twitter>=3.5,<3.6",
    "chardet<6.0",
    "pymongo>=3.8,<3.12",
    "croniter<6.1",
    "python-dateutil<2.10",
    "unidecode>=0.04.21,<=1.3.8",
    "authlib>0.14,<1.5",
    "draftjs-exporter[lxml]<5.1",
    "regex>=2020.7.14,<=2024.11.6",
    "flask-oidc-ex>=0.5.5,<0.7",
    "elastic-apm[flask]>=6.15.1,<7.0",
    # Fix an issue with MarkupSafe 2.1.0 not exporting `soft_unicode`
    "MarkupSafe<2.1",
    "reportlab>=3.6.11,<4.3",
    "pyjwt>=2.4.0,<2.11",
    "Werkzeug>=1.0,<1.1",
    "Jinja2>=2.11,<3.0",
    "Click>=8.0.3,<9.0",
    "itsdangerous>=1.1,<2.0",
    "pymemcache>=4.0,<4.1",
    "xmlsec>=1.3.13,<1.3.15",
    "mongolock @ git+https://github.com/superdesk/mongolock.git@v1",
]

package_data = {
    "superdesk": [
        "templates/*.txt",
        "templates/*.html",
        "locators/data/*.json",
        "io/data/*.json",
        "data_updates/*.py",
        "data_updates/*.js",
        "translations/*.po",
        "translations/*.mo",
    ],
    "apps": [
        "prepopulate/*.json",
        "prepopulate/data_init/*.json",
        "io/data/*.json",
    ],
}

setup(
    name="Superdesk-Core",
    version="2.9.0.dev",
    description="Superdesk Core library",
    long_description=LONG_DESCRIPTION,
    author="petr jasek",
    author_email="petr.jasek@sourcefabric.org",
    url="https://github.com/superdesk/superdesk-core",
    license="GPLv3",
    platforms=["any"],
    packages=find_packages(exclude=["tests*", "features*"]),
    package_data=package_data,
    include_package_data=True,
    # setup_requires=["setuptools_scm"],
    install_requires=install_requires,
    extras_require={
        "exiv2": ["pyexiv2>=2.12.0,<2.16"],
    },
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
)
