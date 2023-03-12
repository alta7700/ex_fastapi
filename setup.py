from setuptools import setup, find_packages

version = '0.1.2'


setup(
    name='tascan-ex-fastapi',
    version=version,

    author='alta7700',
    author_email='alta7700@mail.ru',

    packages=find_packages(),
    package_dir={'ex_fastapi': 'ex_fastapi'},
    package_data={'ex_fastapi': ['templates/*.html']},

    install_requires=[
        'fastapi[all]==0.94.0',
        'phonenumbers==8.13.7',
        'passlib==1.7.4',
        'PyJWT==2.6.0',
        'cryptography==39.0.2',
    ],

    python_requires='>=3.11',
)
