"""TOML configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from .fixtures import FixtureConfig, validate_fixture_set

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "fixtures.toml"


@dataclass(frozen=True, slots=True)
class ControllerConfig:
    artnet_host: str
    artnet_port: int
    universe: int
    fps: int
    fixtures: tuple[FixtureConfig, ...]

    def __post_init__(self) -> None:
        if not self.artnet_host:
            raise ValueError("artnet_host cannot be empty")
        if not 1 <= self.artnet_port <= 65535:
            raise ValueError("artnet_port must be between 1 and 65535")
        if not 0 <= self.universe <= 32767:
            raise ValueError("universe must be between 0 and 32767")
        if not 1 <= self.fps <= 60:
            raise ValueError("fps must be between 1 and 60")
        validate_fixture_set(self.fixtures)


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> ControllerConfig:
    config_path = Path(path)
    with config_path.open("rb") as stream:
        data = tomllib.load(stream)

    try:
        controller = data["controller"]
        fixture_records = data["fixtures"]
        fixtures = tuple(FixtureConfig(**record) for record in fixture_records)
        return ControllerConfig(
            artnet_host=controller["artnet_host"],
            artnet_port=controller["artnet_port"],
            universe=controller["universe"],
            fps=controller["fps"],
            fixtures=fixtures,
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"invalid configuration in {config_path}: {exc}") from exc
