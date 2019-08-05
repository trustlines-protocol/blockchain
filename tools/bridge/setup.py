from setuptools import find_packages, setup

setup(
    name="tlbc-bridge",
    packages=find_packages(),
    entry_points={"console_scripts": ["tlbc-bridge=bridge.main:main"]},
)
