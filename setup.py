from setuptools import setup
import os

version = "1.2.2"
tag = os.getenv("TRAVIS_TAG")
assert not tag or tag==version, "Travis tag has to match version: %r!=%r" % (tag, version)

setup(
    name="pylgbst",
    version=version,

    author="Andrey Pokhilko",
    author_email="apc4@ya.ru",
    license="MIT",
    description="Python library to interact with LEGO PoweredUp devices (Lego BOOST etc.)",
    url='https://github.com/undera/pylgbst',
    keywords=['LEGO', 'ROBOTICS', 'BLUETOOTH'],

    packages=["pylgbst", "pylgbst.comms"],
    requires=[],
    extras_require={
        # Note that dbus and gi are normally system packages
        "gatt": ["gatt", "dbus", "gi"],
        "gattlib": ["gattlib"],
        "pygatt": ["pygatt", "pexpect"],
        "bluepy": ["bluepy"],
        "bleak": ["bleak"],
    },
)
