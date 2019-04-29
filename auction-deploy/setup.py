from setuptools import setup, find_packages

setup(
    name="auction-deploy",
    setup_requires=["setuptools_scm"],
    # use_scm_version=True,
    version="0.0.1",
    packages=find_packages(),
    package_data={"auction_deploy": ["contracts.json"]},
    install_requires=["click"],
    entry_points="""
    [console_scripts]
    auction-deploy=auction_deploy.cli:main
    """,
)
