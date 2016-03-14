#!/usr/bin/env python
from setuptools import setup, find_packages

from pip.req import parse_requirements

install_reqs = parse_requirements('requirements.txt', session=False)
install_requires = [str(ir.req) for ir in install_reqs]

# requirements
requirements = {
    'setup_requires': [],
    'install_requires': install_requires,
    'tests_require': []
}

setup(
    name="sonos-yamaha-monitor",
    version="0.1.0",
    description="SONOS Yamaha Monitor",
    author='Wylie Swanson',
    author_email='wylie@pingzero.net',
    url='',
    data_files=[],
    setup_requires=requirements['setup_requires'],
    tests_require=requirements['tests_require'],
    install_requires=requirements['install_requires'],
    entry_points={
        'console_scripts': ['sonos-yamaha-monitor = sonos-yamaha-monitor:main']
    },
    packages=find_packages("."),
)
