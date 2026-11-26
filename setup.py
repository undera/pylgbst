from setuptools import setup
import os

version = "2.0.0"
tag = os.getenv("TRAVIS_TAG")
assert not tag or tag == version, "Travis tag has to match version: %r!=%r" % (tag, version)

setup(
    name="pylgbst",
    version=version,

    author="Andrey Pokhilko",
    author_email="andrei.pokhilko@gmail.com",
    license="MIT",
    description="Python library to interact with LEGO PoweredUp devices (Lego BOOST etc.)",
    url='https://github.com/undera/pylgbst',
    keywords=['LEGO', 'ROBOTICS', 'BLUETOOTH'],

    packages=["pylgbst", "pylgbst.comms", "pylgbst.aio"],
    install_requires=["bleak"],
    extras_require={
        "bleak": [],  # kept for `pip install pylgbst[bleak]` written before bleak became the only backend
    },
)
