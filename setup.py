import codecs
import os
from setuptools import setup, find_packages

from eplus_rmd import VERSION

this_dir = os.path.abspath(os.path.dirname(__file__))
with codecs.open(os.path.join(this_dir, 'README.md'), encoding='utf-8') as i_file:
    long_description = i_file.read()

setup(
    name='createRulesetModelDescription',
    version=VERSION,
    packages=find_packages(exclude=['test', 'tests', 'test.*']),
    url='https://github.com/JasonGlazer/createRulesetModelDescription',
    license='',
    author='Jason Glazer',
    author_email='',
    description='A Python tool for generating RMDs.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    test_suite='nose.collector',
    tests_require=['nose'],
    keywords='energyplus',
    include_package_data=True,
    install_requires=[],
    entry_points={
        'console_scripts': [
            'create_rmd=eplus_rmd.runner:run',
        ],
    },
    python_requires='>=3.5',
)
