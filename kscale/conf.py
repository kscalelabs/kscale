"""Defines the bot environment settings."""

import functools
import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from omegaconf import II, OmegaConf


def get_path() -> Path:
    if "KSCALE_CONFIG_DIR" in os.environ:
        return Path(os.environ["KSCALE_CONFIG_DIR"]).expanduser().resolve()
    return Path("~/.kscale/").expanduser().resolve()


@dataclass
class StoreSettings:
    api_key: str = field(default=II("oc.env:KSCALE_API_KEY"))

    def get_api_key(self) -> str:
        try:
            return self.api_key
        except AttributeError:
            raise ValueError(
                "API key not found! Get one here and set it as the `KSCALE_API_KEY` "
                "environment variable: https://kscale.store/keys"
            )


@dataclass
class Settings:
    store: StoreSettings = StoreSettings()

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
            OmegaConf.save(config, dir_path / "settings.yaml")
        else:
            with open(dir_path / "settings.yaml", "r") as f:
                raw_settings = OmegaConf.load(f)
                config = OmegaConf.merge(config, raw_settings)
        return config
