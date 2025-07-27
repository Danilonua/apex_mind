from setuptools import setup

setup(
    name="apex",
    version="0.1",
    py_modules=["apex"],
    install_requires=["typer[all]"],
    entry_points={
        "console_scripts": [
            "apex = apex:app",
        ],
    },
)
