from __future__ import absolute_import, division, print_function

import os

from setuptools import setup

base_dir = os.path.dirname(__file__)

setup(
    name='twisted_s3',
    packages=['twisted_s3'],
    description='Asynchronous HTTP client for interacting with Amazon S3',
    url='https://github.com/Yelp/twisted_s3',
    author='Yelp Performance Team',
    author_email='no-reply+use_github_issues@yelp.com',
    platforms='all',
    py_modules=['twisted_s3'],
    install_requires=[
        'fido >= 2.1.0',
        'six',
    ],
    extras_require={
        ':python_version!="2.6"': ['twisted >= 14.0.0'],
        ':python_version=="2.6"': ['twisted >= 14.0.0, < 15.5'],
    },
    options={
        'bdist_wheel': {
            'universal': 1,
        },
    },
    version='0.2.0',
)
