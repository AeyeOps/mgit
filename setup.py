#!/usr/bin/env python
"""Setup script for mgit."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mgit",
    version="0.2.3",
    author="Steve Antonakakis",
    author_email="steve.antonakakis@gmail.com",
    description="Multi-provider Git management tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AeyeOps/mgit",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.9.0",
        "azure-devops>=7.1.0b1",
        "python-dotenv>=1.0.0",
        "rich>=13.0.0",
        "typer>=0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "mgit=mgit.__main__:entrypoint",
        ],
    },
    license="MIT",
    include_package_data=True,
)