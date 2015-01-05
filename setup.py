import os

from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()

requires = [
    'clld>=0.16',
    'clldmpg',
    'transaction',
    'pyramid_tm',
    'zope.sqlalchemy',
    'waitress',
    'python-docx',
    'pycountry',
]

setup(name='tsammalex',
      version='0.0',
      description='tsammalex',
      long_description=README,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web pyramid pylons',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="tsammalex",
      entry_points="""\
[paste.app_factory]
main = tsammalex:main
""",
      )
