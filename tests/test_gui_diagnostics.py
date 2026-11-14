from scripts import capture_gui_diagnostics
from scripts.capture_gui_diagnostics import redact_sensitive_output


def test_gui_diagnostics_redact_private_runtime_configuration():
    source = (
        "BHF_DATA_DIR=/app/.private-data\n"
        '"BHF_CLOUDKIT_API_TOKEN": "example-private-token"\n'
        "Authorization: Bearer example-bearer-token\n"
        "startup exception: Permission denied while creating /app/.bhf-data/file\n"
    )

    redacted = redact_sensitive_output(source)

    assert "/app/.private-data" not in redacted
    assert "example-private-token" not in redacted
    assert "example-bearer-token" not in redacted
    assert "Permission denied" in redacted


def test_gui_diagnostics_capture_compose_state_and_web_logs_before_cleanup(tmp_path, monkeypatch, capsys):
    calls = []

    def fake_run(command):
        calls.append(list(command))
        if command[-2:] == ["ps", "-aq"]:
            return 0, "container-id\n"
        if "logs" in command:
            return 0, "BHF_CLOUDKIT_API_TOKEN=private-value\nstartup exception: Permission denied\n"
        return 0, "state captured\n"

    monkeypatch.setattr(capture_gui_diagnostics, "_run", fake_run)
    capture_gui_diagnostics.capture(tmp_path)

    assert calls[0][-2:] == ["ps", "-a"]
    assert calls[1][-3:] == ["logs", "--no-color", "bhf-web"]
    assert calls[2][-2:] == ["ps", "-aq"]
    assert "container-id" in calls[3]
    web_log = (tmp_path / "bhf-web.log").read_text(encoding="utf-8")
    assert "private-value" not in web_log
    assert "Permission denied" in web_log
    assert "uid=" in (tmp_path / "host-runtime-filesystem.txt").read_text(encoding="utf-8")
    assert (tmp_path / "bhf-web.log").stat().st_mode & 0o777 == 0o600
    assert "private-value" not in capsys.readouterr().out
