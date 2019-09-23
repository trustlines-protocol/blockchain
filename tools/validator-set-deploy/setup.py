from setuptools import find_packages, setup

setup(
    name="validator-set-deploy",
    setup_requires=["setuptools_scm"],
    # use_scm_version=True,
    version="0.0.1",
    packages=find_packages(),
    package_data={"validator_set_deploy": ["contracts.json"]},
    install_requires=["click", "web3", "contract-deploy-tools"],
    entry_points="""
    [console_scripts]
    validator-set-deploy=validator_set_deploy.cli:main
    """,
)
