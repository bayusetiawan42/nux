# tests/test_knowledge.py
# Persistent knowledge store tests.

from sharkyo.storage.knowledge import KnowledgeManager


def test_set_get_list():
    km = KnowledgeManager()
    km.set("Editor", "neovim")
    km.set("Shell", "zsh")
    assert km.get("editor") == "neovim"
    entries = dict(km.list_all())
    assert entries == {"editor": "neovim", "shell": "zsh"}


def test_set_overwrites():
    km = KnowledgeManager()
    km.set("dir", "~/Projects")
    km.set("dir", "~/dev")
    assert km.get("dir") == "~/dev"
    assert len(km.list_all()) == 1


def test_delete_and_clear():
    km = KnowledgeManager()
    km.set("a", "1")
    assert km.delete("a") is True
    assert km.get("a") is None
    assert km.delete("a") is False

    km.set("b", "2")
    km.clear()
    assert km.list_all() == []