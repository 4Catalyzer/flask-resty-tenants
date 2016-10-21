from setuptools import Command, setup, find_packages
import subprocess

# -----------------------------------------------------------------------------


def system(command):
    class SystemCommand(Command):
        user_options = []

        def initialize_options(self):
            pass

        def finalize_options(self):
            pass

        def run(self):
            subprocess.check_call(command, shell=True)

    return SystemCommand


# -----------------------------------------------------------------------------

setup(
    name="Flask-RESTy-Tenants",
    version='0.5.1',
    description='Flask Resty Authorization module for multitenancy',
    url='https://github.com/4Catalyzer/flask-resty-tenants',
    author='Giacomo Tagliabue',
    author_email='giacomo.tag@gmail.com',
    license='MIT',
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Framework :: Flask',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ),
    keywords='rest flask multitenancy',
    packages=find_packages(exclude=('tests',)),
    install_requires=(
        'Flask >= 0.10',
        'Flask-RESTy >= 0.10.0',
        'SQLAlchemy >= 1.0.0'
    ),
    cmdclass={
        'clean': system('rm -rf build dist *.egg-info'),
        'package': system('python setup.py pandoc sdist bdist_wheel'),
        'pandoc': system('pandoc README.md -o README.rst'),
        'publish': system('twine upload dist/*'),
        'release': system('python setup.py clean package publish'),
        'test': system('tox'),
    },
)
