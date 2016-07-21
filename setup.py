from __future__ import absolute_import, division, print_function

import os

from setuptools import setup

base_dir = os.path.dirname(__file__)

setup(
    name='twisted_s3',
    packages=['twisted_s3'],
    install_requires=[
        'fido >= 2.1.0',
        'six',
    ],
    extras_require={
        ':python_version!="2.6"': ['twisted >= 14.0.0'],
        ':python_version=="2.6"': ['twisted >= 14.0.0, < 15.5'],
    },
    version="0.1.0",
)
