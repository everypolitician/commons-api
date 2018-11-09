from setuptools import setup, find_packages

setup(
    name='commons-api',
    version='0.1',
    description='Experimental Democratic Commons explorer and API'
    #long_description=open('README.rst').read(),
    author='Democracy Team, mySociety',
    author_email='democracy@mysociety.org',
    url='https://github.com/alexsdutton/commons-api',
    license='BSD',
    packages=find_packages(exclude=("test*", )),
    install_requires=['Django'],
)

