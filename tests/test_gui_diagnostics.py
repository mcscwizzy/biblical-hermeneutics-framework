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
