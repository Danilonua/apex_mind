from setuptools import setup, find_packages
from pyo3_build_config import BuildConfig

setup(
    name="wasi_security_layer",
    version="0.1.0",
    packages=find_packages(),
    package_data={
        "wasi_security_layer": ["libwasi_security_layer.so"],
    },
    zip_safe=False,
    rust_extensions=[BuildConfig.pyextension()],
)