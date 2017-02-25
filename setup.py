import sys
from distutils.core import setup


if not sys.version_info[0] == 3:
    sys.exit("[ERROR] Package syncrhrophasor is only available for Python 3.")


setup(name = 'synchrophasor',
      packages = ['synchrophasor'],
      version = '1.0.0-alpha',
      description = 'Synchrophasor module represents implementation of IEEE C37.118.2 standard in Python.',
      author = 'Stevan Sandi, Tomo Popovic, Bozo Krstajic',
      author_email = 'stevan.sandi@gmail.com',
      license = "BSD-3",
      url = 'https://github.com/iicsys/pypmu',
      download_url = 'https://github.com/iicsys/pypmu/tarball/1.0.0-alpha',
      keywords = ['synchrophasor', 'pypmu', 'pdc', 'pmu', 'power-systems', 'ieeec37118'],
      classifiers=[
                    "Development Status :: 3 - Alpha",
                    "Intended Audience :: Science/Research",
                    "Programming Language :: Python :: 3",
                    "Topic :: Scientific/Engineering",
                    "License :: OSI Approved :: BSD License",
      ],
)