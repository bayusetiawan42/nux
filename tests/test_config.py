# tests/test_config.py
# Config file parsing tests.

import pytest

from nux.core.config import load_config


def _patch_rc(monkeypatch, tmp_path, content: str) -> None:
    rc = tmp_path / ".nuxrc"
    rc.write_text(content, encoding="utf-8")
    monkeypatch.setattr("nux.core.config.RC_FILE", str(rc))


@pytest.mark.parametrize(
    "syntax",
    [
        "set max_history 8\n",
        "max_history = 8\n",
        "max_history: 8\n",
    ],
)
def test_supported_syntaxes(monkeypatch, tmp_path, syntax):
    _patch_rc(monkeypatch, tmp_path, syntax)
    assert load_config().max_history == 8


def test_missing_rc_returns_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr("nux.core.config.RC_FILE", str(tmp_path / "does-not-exist"))
    cfg = load_config()
    assert cfg.model == "openai/gpt-oss-20b"
    assert cfg.max_history == 12
    assert cfg.temperature == 0.7


def test_comments_and_invalid_lines_ignored(monkeypatch, tmp_path):
    _patch_rc(monkeypatch, tmp_path, "# comment\n\nbogus line\nmax_completion_tokens = 128\n")
    assert load_config().max_completion_tokens == 128


def test_invalid_value_keeps_default(monkeypatch, tmp_path):
    _patch_rc(monkeypatch, tmp_path, "max_history = not-a-number\n")
    assert load_config().max_history == 12
