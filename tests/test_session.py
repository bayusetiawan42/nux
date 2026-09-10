# tests/test_session.py
# Session tests: create(), get_environment_context(), config handling.



from nux.server.daemon import Session
from nux.server.protocol import Packet


class TestSessionCreate:
    def test_create_with_prompt(self):
        session = Session.create("test prompt")
        assert session.packet.message["prompt"] == "test prompt"
        assert session.packet.type == "CLIENT"
        assert session.config is not None

    def test_create_with_cwd(self):
        session = Session.create("test", cwd="/tmp")
        assert session.packet.cwd == "/tmp"

    def test_create_with_existing_packet(self):
        packet = Packet(
            type="CLIENT",
            version="0.1.0",
            cwd="/test",
            message={"prompt": "from packet"},
        )
        session = Session.create("ignored", packet=packet)
        assert session.packet.message["prompt"] == "from packet"
        assert session.packet.cwd == "/test"

    def test_create_config_is_loaded(self):
        session = Session.create("test")
        assert hasattr(session.config, "model")
        assert hasattr(session.config, "max_history")

    def test_create_with_custom_config(self):
        session = Session.create("test")
        # Config should have default values
        assert session.config.model == "openai/gpt-oss-120b"
        assert session.config.max_history == 12


class TestSessionEnvironmentContext:
    def test_get_environment_context(self):
        session = Session.create("test", cwd="/tmp")
        context = session.get_environment_context()
        assert "Working Directory: /tmp" in context
        assert "Current Time:" in context

    def test_get_environment_context_includes_git_info(self, monkeypatch):
        def mock_run_cmd(cmd, args=None):
            if cmd == "git" and args == ["config", "--get", "remote.origin.url"]:
                return "https://github.com/test/repo.git"
            if cmd == "git" and args == ["branch", "--show-current"]:
                return "main"
            return ""

        monkeypatch.setattr("nux.server.daemon._run_cmd", mock_run_cmd)

        session = Session.create("test", cwd="/tmp")
        context = session.get_environment_context()
        assert "Git Remote (origin): https://github.com/test/repo.git" in context
        assert "Git Branch: main" in context

    def test_get_environment_context_no_git(self, monkeypatch):
        monkeypatch.setattr("nux.server.daemon._run_cmd", lambda cmd, args=None: "")

        session = Session.create("test", cwd="/tmp")
        context = session.get_environment_context()
        assert "Git Remote" not in context
        assert "Git Branch" not in context


class TestSessionDataclass:
    def test_session_equality(self):
        packet = Packet(type="CLIENT", version="1.0", cwd="/tmp", message={"prompt": "hi"})
        from nux.core.config import Config

        config = Config()
        s1 = Session(config=config, packet=packet)
        s2 = Session(config=config, packet=packet)
        assert s1 == s2

    def test_session_fields(self):
        packet = Packet(type="CLIENT", version="1.0", cwd="/tmp", message={"prompt": "hi"})
        from nux.core.config import Config

        config = Config()
        session = Session(config=config, packet=packet)
        assert session.config is config
        assert session.packet is packet
