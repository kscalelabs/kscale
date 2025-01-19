"""Defines the bot environment settings."""

import functools
import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from omegaconf import II, OmegaConf

# This is the public API endpoint for the K-Scale WWW API.
DEFAULT_API_ROOT = "https://api.kscale.dev"

SETTINGS_FILE_NAME = "settings.yaml"


def get_path() -> Path:
    if "KSCALE_CONFIG_DIR" in os.environ:
        return Path(os.environ["KSCALE_CONFIG_DIR"]).expanduser().resolve()
    return Path("~/.kscale/").expanduser().resolve()


@dataclass
class WWWSettings:
    api_root: str = field(default=DEFAULT_API_ROOT)
    base_dir: str = field(default=II("oc.env:KSCALE_DIR,'~/.kscale/'"))
    refresh_interval_minutes: int = field(default=60 * 24)


@dataclass
class Settings:
    www: WWWSettings = field(default_factory=WWWSettings)

    def save(self) -> None:
        (dir_path := get_path()).mkdir(parents=True, exist_ok=True)
        with open(dir_path / "settings.yaml", "w") as f:
            OmegaConf.save(config=self, f=f)

    @functools.lru_cache
    @staticmethod
    def load() -> "Settings":
        config = OmegaConf.structured(Settings)
        if not (dir_path := get_path()).exists():
            warnings.warn(f"Settings directory does not exist: {dir_path}. Creating it now.")
            dir_path.mkdir(parents=True)
            OmegaConf.save(config, dir_path / SETTINGS_FILE_NAME)
        else:
            try:
                with open(dir_path / SETTINGS_FILE_NAME, "r") as f:
                    raw_settings = OmegaConf.load(f)
                    config = OmegaConf.merge(config, raw_settings)
            except Exception as e:
                warnings.warn(f"Failed to load settings: {e}")
        return config
