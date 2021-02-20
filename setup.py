import setuptools

with open('requirements.txt') as f:
    required = f.read().splitlines()

setuptools.setup(
    name="botocache",
    author="rams3sh",
    version="0.0.4",
    description="Caching for Boto and Boto3 SDK",
    packages=["botocache"],
    install_requires=required,
    python_requires='>=3.5',
)