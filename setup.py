from pathlib import Path
from setuptools import setup

from energyplus_rpd import VERSION

readme_file = Path(__file__).parent.resolve() / 'README.md'
readme_contents = readme_file.read_text()

setup(
    name='energyplus_ruleset_model',
    version=VERSION,
    packages=['energyplus_rpd'],
    url='https://github.com/JasonGlazer/createRulesetProjectDescription',
    license='ModifiedBSD',
    author='Jason Glazer',
    description='A Python tool for generating RPDs.',
    package_data={
        "energyplus_rpd": [
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
    install_requires=['jsonschema==4.17', 'pyyaml'],
    entry_points={
        'console_scripts': [
            'createRulesetProjectDescription=energyplus_rpd.runner:run',
        ],
    },
    python_requires='>=3.7',
)
