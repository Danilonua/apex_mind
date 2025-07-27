from setuptools import setup, find_packages

setup(
    name="apex_mind_core",
    version="0.1.0",
    packages=find_packages(include=['apex_mind_core', 'apex_mind_core.*']),  # Фикс здесь!
    install_requires=[
        "typer",
        "requests",
        "wasi_security_layer @ file:///C:/Users/danil/Desktop/apex-mind-core_v0.1/wasi_security_layer"
    ],
    entry_points={
        "console_scripts": [
            "apex = apex:app",
        ],
    },
)