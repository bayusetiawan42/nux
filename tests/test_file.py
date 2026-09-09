# tests/test_file.py
# FILE tools tests: argument parsing, including null/missing handling.

from nux.tools.file import FileEditArgs, FileReadArgs, FileWriteArgs


class TestReadArgs:
    def test_from_dict(self):
        parsed = FileReadArgs.from_dict({"path": "/x", "offset": 5, "limit": 100})
        assert parsed.path == "/x"
        assert parsed.offset == 5
        assert parsed.limit == 100

    def test_missing_fields_default(self):
        parsed = FileReadArgs.from_dict({"path": "/x"})
        assert parsed.offset == 1
        assert parsed.limit == 2000

    def test_null_fields_do_not_crash(self):
        parsed = FileReadArgs.from_dict({"path": "/x", "offset": None, "limit": None})
        assert parsed.offset == 1
        assert parsed.limit == 2000

    def test_zero_and_negative_clamped(self):
        parsed = FileReadArgs.from_dict({"path": "/x", "offset": 0, "limit": -5})
        assert parsed.offset == 1
        assert parsed.limit == 1


class TestWriteArgs:
    def test_from_dict(self):
        parsed = FileWriteArgs.from_dict({"path": "/x", "content": "hi"})
        assert parsed.path == "/x"
        assert parsed.content == "hi"

    def test_null_content_does_not_crash(self):
        parsed = FileWriteArgs.from_dict({"path": "/x", "content": None})
        assert parsed.content == ""


class TestEditArgs:
    def test_from_dict(self):
        parsed = FileEditArgs.from_dict(
            {"path": "/x", "old_string": "a", "new_string": "b"}
        )
        assert parsed.old_string == "a"
        assert parsed.new_string == "b"

    def test_null_strings_do_not_crash(self):
        parsed = FileEditArgs.from_dict(
            {"path": "/x", "old_string": None, "new_string": None}
        )
        assert parsed.old_string == ""
        assert parsed.new_string == ""