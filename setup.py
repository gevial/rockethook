# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='rockethook',
    version='1.0.0',
    description='Simple library for posting to Rocket.Chat via webhooks a.k.a. integrations.',
    long_description=readme,
    author='Gennady Aleksandrov',
    author_email='gevial@yahoo.com',
    url='https://github.com/gevial/rockethook',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)
