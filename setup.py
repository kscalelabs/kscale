# mypy: disable-error-code="import-untyped, import-not-found"
#!/usr/bin/env python
"""Setup script for the project."""

import re
import subprocess

from setuptools import find_packages, setup
from setuptools.command.build_ext import build_ext
from setuptools_rust import Binding, RustExtension

with open("README.md", "r", encoding="utf-8") as f:
    long_description: str = f.read()


with open("kscale/requirements.txt", "r", encoding="utf-8") as f:
    requirements: list[str] = f.read().splitlines()


with open("kscale/requirements-dev.txt", "r", encoding="utf-8") as f:
    requirements_dev: list[str] = f.read().splitlines()


with open("kscale/__init__.py", "r", encoding="utf-8") as fh:
    version_re = re.search(r"^__version__ = \"([^\"]*)\"", fh.read(), re.MULTILINE)
assert version_re is not None, "Could not find version in kscale/__init__.py"
version: str = version_re.group(1)


class RustBuildExt(build_ext):
    def run(self) -> None:
        subprocess.run(["cargo", "run", "--bin", "stub_gen"], check=True)
        super().run()


setup(
    name="kscale",
    version=version,
    description="The kscale project",
    author="Benjamin Bolte",
    license_files=("LICENSE",),
    url="https://github.com/kscalelabs/kscale",
    rust_extensions=[
        RustExtension(
            target="kscale.rust",
            path="kscale/rust/Cargo.toml",
            binding=Binding.PyO3,
        ),
    ],
    setup_requires=["setuptools-rust"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.11",
    install_requires=requirements,
    tests_require=requirements_dev,
    zip_safe=False,
    extras_require={"dev": requirements_dev},
    include_package_data=True,
    packages=find_packages(include=["kscale"]),
    cmdclass={"build_ext": RustBuildExt},
    entry_points={
        "console_scripts": [
            "kscale = kscale.cli:cli",
        ],
    },
)
