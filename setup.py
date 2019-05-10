#!/usr/bin/env python3

from setuptools import setup
from aioax25 import __version__

requirements = [
        'pyserial',
        'signalslot',
]

setup(
        name='aioax25',
        url='https://github.com/sjlongland/aioax25/',
        version=__version__,
        author='Stuart Longland VK4MSL',
        author_email='me@vk4msl.id.au',
        license='GPL-2.0-or-later',
        packages=[
            'aioax25',
            'aioax25.aprs',
        ],
        requires=requirements,
        install_requires=requirements
)
