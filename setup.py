from setuptools import setup, find_packages

setup(
    name="toolshed",
    version="0.1",
    packages=find_packages(),
    install_requires=["django", "jsonschema","psycopg2"],
    author="Mike Grimsley",
    author_email="xmikegrim@gmail.com",
    description="A library for managing tool use with an open ai client",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/mgrimsl/toolshed",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)