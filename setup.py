from setuptools import setup, find_packages

version = '0.1.0'


setup(
    name='tascan-ex-fastapi',
    version=version,

    author='alta7700',
    author_email='alta7700@mail.ru',

    packages=find_packages(),
    package_dir={'ex_fastapi': 'ex_fastapi'},
    package_data={'ex_fastapi': ['templates/*.html']},

    install_requires=[
        'fastapi[all]==0.92.0',
        'phonenumbers==8.13.6',
        'passlib==1.7.4',
        'PyJWT==2.6.0',
        'cryptography==39.0.1',
    ],

    python_requires='>=3.11',
)
