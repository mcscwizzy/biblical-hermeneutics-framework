from __future__ import annotations


def set_viewport(
    driver,
    width: int,
    height: int,
    mobile: bool,
    *,
    screen_width: int | None = None,
    screen_height: int | None = None,
) -> dict[str, int]:
    """Align Chrome's native headless window with its emulated CSS viewport."""
    driver.set_window_size(width, height)
    metrics = {
        "width": width,
        "height": height,
        "deviceScaleFactor": 1,
        "mobile": mobile,
    }
    if screen_width is not None:
        metrics["screenWidth"] = screen_width
    if screen_height is not None:
        metrics["screenHeight"] = screen_height
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", metrics)

    viewport = driver.execute_script(
        "return {innerWidth: window.innerWidth, innerHeight: window.innerHeight, "
        "clientWidth: document.documentElement.clientWidth};"
    )
    assert viewport["innerWidth"] == width, viewport
    assert viewport["clientWidth"] == width, viewport
    assert viewport["innerHeight"] == height, viewport
    return viewport
