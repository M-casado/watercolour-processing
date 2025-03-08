# setup.py

from setuptools import setup, find_packages

setup(
    name="watercolour_processing",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[],
    python_requires=">=3.7",
    description="Watercolour painting processing and metadata management",
    author="Marcos Casado Barbero (0000-0002-7747-6256)",
    url="https://github.com/yourname/watercolour-processing",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
)
