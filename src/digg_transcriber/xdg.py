"""XDG Base Directory paths for digg-transcriber (digg/digg-transcriber namespace)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional


def _home() -> Path:
    return Path.home()


def xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", _home() / ".config")).expanduser()


def xdg_cache_home() -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME", _home() / ".cache")).expanduser()


def xdg_data_home() -> Path:
    return Path(
        os.environ.get("XDG_DATA_HOME", _home() / ".local" / "share")
    ).expanduser()


def dt_config_dir() -> Path:
    return xdg_config_home() / "digg" / "digg-transcriber"


def dt_cache_dir() -> Path:
    return xdg_cache_home() / "digg" / "digg-transcriber"


def dt_data_dir() -> Path:
    return xdg_data_home() / "digg" / "digg-transcriber"


def dt_bin_dir() -> Path:
    return _home() / ".local" / "bin"


def default_config_path() -> Path:
    return dt_config_dir() / "config.yaml"


def config_example_path() -> Path:
    return dt_config_dir() / "config.yaml.example"


def legacy_config_path() -> Path:
    return _home() / ".config" / "digg-transcriber" / "config.yaml"


def dt_hf_home_dir() -> Path:
    return _home() / ".cache" / "huggingface"


def dt_hf_hub_cache_dir() -> Path:
    return dt_hf_home_dir() / "hub"


def legacy_hf_hub_cache_dir() -> Path:
    return _home() / ".cache" / "huggingface" / "hub"


def resolve_config_path(explicit: Optional[Path] = None) -> Path:
    if explicit is not None:
        return explicit.expanduser()
    env = os.environ.get("DIGG_TRANSCRIBER_CONFIG")
    if env:
        return Path(env).expanduser()
    new = default_config_path()
    if new.is_file():
        return new
    legacy = legacy_config_path()
    if legacy.is_file():
        return legacy
    return new


def hf_hub_cache_dir() -> Path:
    if hub := os.environ.get("HF_HUB_CACHE"):
        return Path(hub).expanduser()
    if hf_home := os.environ.get("HF_HOME"):
        return Path(hf_home).expanduser() / "hub"
    new = dt_hf_hub_cache_dir()
    legacy = legacy_hf_hub_cache_dir()
    if new.is_dir() and any(new.iterdir()):
        return new
    if legacy.is_dir() and any(legacy.iterdir()):
        return legacy
    return new


def hf_env_defaults() -> dict[str, str]:
    hf_home = dt_hf_home_dir()
    return {
        "HF_HOME": str(hf_home),
        "HF_HUB_CACHE": str(hf_home / "hub"),
    }


def apply_hf_env_defaults() -> None:
    for key, value in hf_env_defaults().items():
        os.environ.setdefault(key, value)


def ensure_xdg_dirs() -> None:
    for path in (
        dt_config_dir(),
        dt_cache_dir(),
        dt_data_dir(),
        dt_bin_dir(),
        dt_hf_hub_cache_dir(),
        dt_data_dir() / "tool",
    ):
        path.mkdir(parents=True, exist_ok=True)


def migrate_legacy_config(target: Optional[Path] = None) -> Optional[Path]:
    dest = (target or default_config_path()).expanduser()
    legacy = legacy_config_path()
    if dest.is_file() or not legacy.is_file():
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(legacy, dest)
    return dest


__all__ = [
    "xdg_config_home",
    "xdg_cache_home",
    "xdg_data_home",
    "dt_config_dir",
    "dt_cache_dir",
    "dt_data_dir",
    "dt_bin_dir",
    "default_config_path",
    "config_example_path",
    "resolve_config_path",
    "hf_hub_cache_dir",
    "hf_env_defaults",
    "apply_hf_env_defaults",
    "ensure_xdg_dirs",
    "migrate_legacy_config",
]