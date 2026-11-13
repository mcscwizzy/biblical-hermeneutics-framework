from pathlib import Path

import yaml


def test_gui_gate_orders_smoke_and_mobile_acceptance_before_regression():
    compose = yaml.safe_load(Path("docker-compose.selenium.yml").read_text(encoding="utf-8"))
    gui = compose["services"]["gui-tests"]
    command = gui["command"]

    ordered_steps = [
        "gui_connectivity_smoke.py",
        "test_connectivity_smoke.py",
        "test_ed5_mobile_acceptance.py",
        "timeout --signal=INT --kill-after=30s 60m pytest",
    ]
    positions = [command.index(step) for step in ordered_steps]
    assert positions == sorted(positions), command
    assert gui["environment"]["BHF_GUI_BROWSER_HOST"] == "gui-tests"
    assert "--junitxml=/artifacts/ed5-mobile-acceptance.xml" in command
    assert "--junitxml=/artifacts/gui-regression.xml" in command


def test_gui_workflow_probes_selenium_after_healthy_start_and_is_time_bounded():
    workflow = yaml.safe_load(Path(".github/workflows/gui.yml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["gui"]
    steps = job["steps"]
    start = next(index for index, step in enumerate(steps) if step.get("name") == "Start app and Selenium services")
    probe = next(index for index, step in enumerate(steps) if step.get("name") == "Probe application from Selenium container")
    run = next(index for index, step in enumerate(steps) if step.get("name") == "Run ordered GUI gates")

    assert job["timeout-minutes"] == 110
    assert start < probe < run
    assert "--wait" in steps[start]["run"]
    assert 'host, port = "bhf-web", 8080' in steps[probe]["run"]
    assert '("/api/health", "/offline")' in steps[probe]["run"]
