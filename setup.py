from setuptools import setup

setup(
    name="novacluster",
    version="0.0.0",
    author="James J. Porter",
    author_email="porterjamesj@gmail.com",
    description="osdc wrapper around novaclient for launching TORQUE clusters.",
    license="MIT",
    keywords="openstack nova cluster osdc",
    url="https://github.com/porterjamesj/novacluster",
    # longdescription=read("README.md"),
    classifiers=[
        "Environment :: Console",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Utilities",
    ],
    packages=["novacluster"],
    package_data={"novacluster": ["*.yaml", "scripts/*"]},
    entry_points={
        'console_scripts': ['novacluster=novacluster.shell:main']
    },
    install_requires=[
        'python-novaclient==2012.1',
        'pyyaml',
        'M2Crypto'
    ]
)
