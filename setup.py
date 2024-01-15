#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open("README.md") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

with open("requirements.txt") as requirements_file:
    requirements = requirements_file.read()

# requirements = [
#     "typer",
#     "textual",
#     "boto3>=1.28.57",
#     "pandas",
#     "s3fs",
#     "numpy"
# ]

test_requirements = [
    "pytest>=3",
]

setup(
    author="Jillian Rowe",
    author_email="jillian@dabbleofdevops.com",
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="Helper utils for omics",
    entry_points={
        "console_scripts": [
            "bioanalyze-omics=bioanalyze_omics.cli:app",
            "omics-helper=bioanalyze_omics.cli:app",
            "omicsx=bioanalyze_omics.cli:app",
        ],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="bioanalyze_omics",
    name="bioanalyze_omics",
    packages=find_packages(include=["bioanalyze_omics", "bioanalyze_omics.*"]),
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/dabble-of-devops-bioanalyze/omics-helper",
    version="0.1.0",
    zip_safe=False,
)
