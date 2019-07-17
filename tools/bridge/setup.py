from setuptools import setup, find_packages

setup(
    name="tlbc-bridge",
    packages=find_packages(),
    entry_points={"console_scripts": ["tlbc-bridge=bridge.main:main"]},
)
