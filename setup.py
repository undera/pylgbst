from setuptools import setup

version = "2.0.0"

setup(
    name="pylgbst",
    version=version,

    author="Andrey Pokhilko",
    author_email="andrei.pokhilko@gmail.com",
    license="MIT",
    description="Python library to interact with LEGO PoweredUp devices (Lego BOOST etc.)",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url='https://github.com/undera/pylgbst',
    keywords=['LEGO', 'ROBOTICS', 'BLUETOOTH'],

    packages=["pylgbst", "pylgbst.comms", "pylgbst.aio"],
    install_requires=["bleak"],
    extras_require={
        "bleak": [],  # kept for `pip install pylgbst[bleak]` written before bleak became the only backend
    },
)
