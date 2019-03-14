import setuptools
import sys
import re
import os

if sys.version_info < (3, 6):
    print('pysforce in requires at least Python 3.6 to run.')
    sys.exit(1)

with open(os.path.join('pysforce', '__init__.py'), encoding='utf-8') as f:
    version = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M).group(1)

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='pysforce',
    version=version,
    python_requires='>=3.6',
    author='Marshall L Smith Jr',
    author_email='marshallsmithjr@gmail.com',
    description='Salesforce API library',
    long_description = long_description,
    long_description_content_type = 'text/markdown',
    url='https://github.com/mlsmithjr/pysforce',
    packages=['pysforce'],
    install_requires=['requests', 'pyjwt', 'cryptography', 'fastcache'],
    classifiers=[
      'Programming Language :: Python :: 3',
      'Environment :: Console',
      'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
      'Natural Language :: English',
    ],
)

