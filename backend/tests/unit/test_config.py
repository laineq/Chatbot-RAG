from pathlib import Path

from app.core.config import Settings, _read_gemini_api_key_from_file, _read_openai_api_key_from_file


def test_read_openai_api_key_from_plain_file(tmp_path: Path) -> None:
    key_file = tmp_path / "api"
    key_file.write_text("sk-test-abcdefghijklmnopqrstuvwxyz123456\n", encoding="utf-8")

    assert _read_openai_api_key_from_file(key_file) == "sk-test-abcdefghijklmnopqrstuvwxyz123456"


def test_read_openai_api_key_from_rtf_file(tmp_path: Path) -> None:
    key_file = tmp_path / "api.rtf"
    key_file.write_text(
        r"{\rtf1\ansi{\fonttbl\f0\fswiss Helvetica;}\f0\fs24 sk-proj-abcdefghijklmnopqrstuvwxyz1234567890}",
        encoding="utf-8",
    )

    assert _read_openai_api_key_from_file(key_file) == "sk-proj-abcdefghijklmnopqrstuvwxyz1234567890"


def test_ignore_non_openai_api_key_from_rtf_file(tmp_path: Path) -> None:
    key_file = tmp_path / "api.rtf"
    key_file.write_text(
        r"{\rtf1\ansi{\fonttbl\f0\fswiss Helvetica;}\f0\fs24 ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890_abcd}",
        encoding="utf-8",
    )

    assert _read_openai_api_key_from_file(key_file) is None


def test_read_gemini_api_key_from_plain_file(tmp_path: Path) -> None:
    key_file = tmp_path / "api"
    key_file.write_text("AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYz0123456\n", encoding="utf-8")

    assert _read_gemini_api_key_from_file(key_file) == "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYz0123456"


def test_resolved_model_provider_prefers_gemini_when_only_gemini_key_is_set() -> None:
    settings = Settings(gemini_api_key="AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYz0123456")

    assert settings.resolved_model_provider == "gemini"
    assert settings.resolved_api_key == "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYz0123456"
    assert settings.active_chat_model == settings.gemini_chat_model
