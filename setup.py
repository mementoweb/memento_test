# -*- coding: utf-8 -*-
#! /usr/bin/env python3

from setuptools import setup, Command, find_packages
from setuptools.command.test import test as TestCommand
import os
import sys
import glob
import shutil

here = os.path.abspath(os.path.dirname(__file__))


class PyTest(TestCommand):

    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        import multiprocessing
        procs = multiprocessing.cpu_count()

        if procs > 1:
            if type(self.pytest_args) == list:
                self.pytest_args.append("-n " + str(procs))
            elif type(self.pytest_args) == str:
                self.pytest_args += " -n " + str(procs)

        errcode = pytest.main(self.pytest_args)
        sys.exit(errcode)


class BetterClean(Command):
    """Custom clean command to remove other stuff from project root."""
    user_options=[]
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    @staticmethod
    def handle_remove_errors(*args):
        print("Issue removing '" + args[1] + "' (probably does not exist), skipping...")

    def run(self):
        egg_info = glob.glob('*.egg-info')

        for entry in egg_info:
            print("removing " + entry)
            shutil.rmtree(entry)

        shutil.rmtree('build', onerror = BetterClean.handle_remove_errors)
        shutil.rmtree('dist', onerror = BetterClean.handle_remove_errors)


#with open("README.md") as f:
#    readme = f.read()

#with open("LICENSE") as f:
#    license = f.read()

setup(
    name="memento_test",
    version="0.1.3",
    description="A Memento Test Suite",
    keywords="memento http test",
    #long_description=readme,
    author="Harihar Shankar",
    author_email="hariharshankar@gmail.com",
    url="https://github.com/mementoweb/memento_test",
    #license=license,
    zip_safe=False,
    packages=find_packages(exclude=("tests", "docs")),
    scripts=["bin/memento_test_server"],
    include_package_data=True,
    install_requires=["werkzeug>=0.12"],
    test_requires=["pytest"],
    classifiers=[

        'Intended Audience :: Developers',

        'License :: OSI Approved :: BSD License',

        'Operating System :: OS Independent',

        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',

        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4'
    ]
)