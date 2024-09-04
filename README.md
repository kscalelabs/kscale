<p align="center">
  <picture>
    <img alt="K-Scale Open Source Robotics" src="https://media.kscale.dev/kscale-open-source-header.png" style="max-width: 100%;">
  </picture>
</p>

<div align="center">

[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/kscalelabs/ksim/blob/main/LICENSE)
[![Discord](https://img.shields.io/discord/1224056091017478166)](https://discord.gg/k5mSvCkYQh)
[![Wiki](https://img.shields.io/badge/wiki-humanoids-black)](https://humanoids.wiki)
<br />
[![python](https://img.shields.io/badge/-Python_3.11-blue?logo=python&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![black](https://img.shields.io/badge/Code%20Style-Black-black.svg?labelColor=gray)](https://black.readthedocs.io/en/stable/)
[![ruff](https://img.shields.io/badge/Linter-Ruff-red.svg?labelColor=gray)](https://github.com/charliermarsh/ruff)
<br />
[![Python Checks](https://github.com/kscalelabs/kscale/actions/workflows/test.yml/badge.svg)](https://github.com/kscalelabs/kscale/actions/workflows/test.yml)
[![Publish Python Package](https://github.com/kscalelabs/kscale/actions/workflows/publish.yml/badge.svg)](https://github.com/kscalelabs/kscale/actions/workflows/publish.yml)

</div>

# K-Scale Command Line Interface

This is a command line tool for interacting with various services provided by K-Scale Labs, such as:

- [K-Scale Store](https://kscale.store/)

## Installation

```bash
pip install kscale
```

## Usage

### CLI

Download a URDF from the K-Scale Store:

```bash
kscale urdf download <artifact_id>
```

Upload a URDF to the K-Scale Store:

```bash
kscale urdf upload <artifact_id> <root_dir>
```

### Python API

Reference a URDF by ID from the K-Scale Store:

```python
from kscale import KScale

async def main():
  kscale = KScale()
  urdf_dir_path = await kscale.store.urdf("123456")
  print(urdf_dir_path)
```
