from bhf_web.runtime import load_runtime_config


def test_optional_offline_packs_are_not_built_during_interactive_first_load_by_default(monkeypatch):
    monkeypatch.delenv("BHF_AUTO_INSTALL_OFFLINE_PACKS", raising=False)

    assert load_runtime_config()["autoInstallOfflinePacks"] is False


def test_optional_offline_pack_auto_install_can_be_enabled_explicitly(monkeypatch):
    monkeypatch.setenv("BHF_AUTO_INSTALL_OFFLINE_PACKS", "true")

    assert load_runtime_config()["autoInstallOfflinePacks"] is True
