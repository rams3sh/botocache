import setuptools

with open('requirements.txt') as f:
    required = f.read().splitlines()

setuptools.setup(
    name="botocache",
    version="latest",
    author="rams3sh",
    description="Caching for Boto and Boto3 SDK",
    packages=["botocache"],
    install_requires=required,
    python_requires='>=3.6',
)