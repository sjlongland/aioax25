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
        install_requires=requirements,
        description='Asynchronous AX.25 interface in pure Python using asyncio',
        long_description='aioax25 is a library for interfacing Python '\
                'applications to AX.25 networks via serial KISS TNCs.  '\
                'Right now it supports sending and receiving APRS messages '\
                'and can handle multi-port KISS TNCs connected via serial '\
                'ports or pseudo TTYs.',
        classifiers=[
            'Development Status :: 2 - Pre-Alpha',
            'Environment :: No Input/Output (Daemon)',
            'Framework :: AsyncIO',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
            'Operating System :: POSIX',
            'Programming Language :: Python :: 3 :: Only',
            'Topic :: Communications :: Ham Radio'
        ]
)
