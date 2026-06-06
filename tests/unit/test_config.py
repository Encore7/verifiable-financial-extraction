"""Proves the flat src-layout import works and settings load from defaults."""

from config import Settings, get_settings


def test_settings_explicit_value_overrides_default() -> None:
    s = Settings(database_url="postgresql+asyncpg://u:p@h:5432/db")
    assert s.database_url.endswith("/db")


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()
