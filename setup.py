from setuptools import setup, find_packages
from python.version import __version__, __description__

setup(
    name="deepseek-discussion-bot",
    version=__version__,
    description=__description__,
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="deardigital",
    author_email="connect@deardigital.ai",
    url="https://github.com/deardigital-ai/website",
    packages=find_packages(),
    install_requires=[
        "PyGithub==2.1.1",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "rich>=13.7.0",
        "backoff>=2.2.1",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    entry_points={
        "console_scripts": [
            "deepseek-bot=python.main:main",
        ],
    },
) 