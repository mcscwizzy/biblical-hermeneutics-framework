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

    # Let resize handlers run before callers change UI state. The companion
    # listens for viewport changes and applies its breakpoint transition on an
    # animation frame; without these frames, a caller can set a state that the
    # pending breakpoint transition immediately overwrites.
    driver.execute_async_script(
        """
        const done = arguments[0];
        requestAnimationFrame(() => requestAnimationFrame(() => done(true)));
        """
    )

    viewport = driver.execute_script(
        "return {innerWidth: window.innerWidth, innerHeight: window.innerHeight, "
        "clientWidth: document.documentElement.clientWidth};"
    )
    assert viewport["innerWidth"] == width, viewport
    assert viewport["clientWidth"] == width, viewport
    assert viewport["innerHeight"] == height, viewport
    return viewport
