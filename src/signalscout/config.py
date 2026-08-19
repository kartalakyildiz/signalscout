from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

from signalscout.models.enums import SignalType
from signalscout.models.schemas import ResearchProfile

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    playwright_enabled: bool = _env_bool("PLAYWRIGHT_ENABLED", True)
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///database/signalscout.db")

    data_dir: Path = PROJECT_ROOT / "data"
    exports_dir: Path = PROJECT_ROOT / "data" / "exports"
    logs_dir: Path = PROJECT_ROOT / "logs"
    database_dir: Path = PROJECT_ROOT / "database"
    research_profile_path: Path = PROJECT_ROOT / "config" / "research_profile.yaml"

    max_pages_per_company: int = 5
    http_timeout_seconds: float = 10.0
    http_max_retries: int = 2
    min_content_chars: int = 250
    page_content_char_limit: int = 3000
    total_prompt_char_budget: int = 10000


def get_settings() -> Settings:
    return Settings()


def load_research_profile(path: Path | None = None) -> ResearchProfile:
    path = path or get_settings().research_profile_path
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    signals = [SignalType(s) for s in raw.get("signals", [])]
    high_impact = [SignalType(s) for s in raw.get("high_impact_signals", [])]
    qualification = raw.get("qualification", {})

    return ResearchProfile(
        name=raw.get("name", "Research Profile"),
        signals=signals,
        high_impact_signals=high_impact,
        min_validated_signals_high=qualification.get("high", {}).get("minimum_validated_signals", 2),
        min_validated_signals_medium=qualification.get("medium", {}).get("minimum_validated_signals", 1),
    )
