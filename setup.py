from setuptools import setup, find_packages

setup(name='a3update.py',
      version='0.13',
      packages=find_packages(),
      include_package_data=True,
      install_requires=[
          'Click',
          'PyYAML',
          'Py-SteamCMD-Wrapper>=1.1.0',
          'steam',
          'pycryptodomex',
          'pathvalidate',
      ],
      entry_points='''
        [console_scripts]
        a3update=a3update.a3update:cli
      ''',
      )
