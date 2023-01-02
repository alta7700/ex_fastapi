from setuptools import setup, find_packages

version = '0.1.0'


setup(
    name='tascan-ex-fastapi',
    version=version,

    author='alta7700',
    author_email='alta7700@mail.ru',

    packages=find_packages(),

    install_requires=[
        'fastapi[all]>=0.88.0',
        'passlib>=1.7.4',
        'PyJWT>=2.6.0',
        'cryptography>=39.0.0',
    ],

    python_requires='>=3.10',
)
