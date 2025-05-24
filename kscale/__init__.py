"""Defines the common interface for the K-Scale Python API."""

__version__ = "0.3.16"

from pathlib import Path

from kscale.web.clients.client import WWWClient as K

ROOT_DIR = Path(__file__).parent
