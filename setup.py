from pathlib import Path
from setuptools import setup

from eplus_rmd import VERSION

readme_file = Path(__file__).parent.resolve() / 'README.md'
readme_contents = readme_file.read_text()

setup(
    name='eplus_rmd',
    version=VERSION,
    packages=['eplus_rmd'],
    url='https://github.com/JasonGlazer/createRulesetModelDescription',
    license='',
    author='Jason Glazer',
    author_email='',
    description='A Python tool for generating RMDs.',
    package_data={
        "eplus_rmd": [
            "example/*",
            "*.json",
            "*.yaml",
            "*.txt",
        ]
    },
    include_package_data=True,
    long_description=readme_contents,
    long_description_content_type='text/markdown',
    keywords='energyplus',
    install_requires=['jsonschema', 'pyyaml'],
    entry_points={
        'console_scripts': [
            'create_rmd=eplus_rmd.runner:run',
        ],
    },
    python_requires='>=3.7',
)
