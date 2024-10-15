"""Defines some helper functions for working with artifacts."""

from pathlib import Path

ARTIFACTS_DIR = Path(__file__).parent.resolve()

PLANE_OBJ_PATH = ARTIFACTS_DIR / "plane.obj"
PLANE_URDF_PATH = ARTIFACTS_DIR / "plane.urdf"
