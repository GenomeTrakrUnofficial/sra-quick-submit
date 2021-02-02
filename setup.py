#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [ ]

setup_requirements = [ ]

test_requirements = [ ]

setup(
    author="Justin Payne",
    author_email='justin.payne@fda.hhs.gov',
    python_requires='>=3.5',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Pip package for SRA Quick-Submit, a goofy SRA submission tool from 2013.",
    entry_points={
        'console_scripts': [
            'sra-quick-submit=sra_quick_submit_package.sra_quick_submit:main'
        ]
    },
    install_requires=requirements,
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='sra_quick_submit_package',
    name='sra_quick_submit_package',
    packages=find_packages(include=['sra_quick_submit_package', 'sra_quick_submit_package.*']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/crashfrog/sra_quick_submit',
    version='1.8',
    zip_safe=False,
)
