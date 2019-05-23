from setuptools import setup, find_packages

setup(
    name="bridge-deploy",
    setup_requires=["setuptools_scm"],
    # use_scm_version=True,
    version="0.0.1",
    packages=find_packages(),
    package_data={"bridge_deploy": ["contracts.json"]},
    install_requires=["click", "web3", "contract-deploy-tools", "pendulum"],
    entry_points="""
    [console_scripts]
    bridge-deploy=bridge_deploy.cli:main
    """,
)
