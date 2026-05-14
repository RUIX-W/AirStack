---
name: isaac-sim-webrtc-streaming
description: Non-obvious Isaac Sim 5.1 API facts for WebRTC browser streaming from a standalone Python scene. Read this before attempting to add streaming to a launch script.
license: Apache-2.0
metadata:
  author: AirLab CMU
  repository: AirStack
---

# Skill: Isaac Sim WebRTC Streaming — What the Docs Don't Tell You

## The Correct Pattern

```python
from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": True, "hide_ui": False})

from isaacsim.core.utils.extensions import enable_extension
simulation_app.set_setting("/app/window/drawMouse", True)
enable_extension("omni.kit.livestream.webrtc")

# normal standalone physics loop — world.step(render=True) drives both physics and streaming
```

That's it. The extension handles everything else.

## Four Things That Will Waste Your Time

### 1. `SimulationApp({"livestream": 2})` is a silent no-op in Isaac Sim 5.1

The `"livestream"` key was removed from `SimulationApp.DEFAULT_LAUNCHER_CONFIG` in Isaac Sim 5.x. Passing it is silently ignored — no streaming extension loads, no port opens, no error is raised. It was valid in Isaac Sim 2022/2023 but does nothing here.

### 2. `omni.kit.livestream.websocket` does not exist in Isaac Sim 5.1

This extension was present in older versions. In Isaac Sim 5.1 the only streaming extensions are:

- `omni.kit.livestream.webrtc` — WebRTC streaming (use this for the browser viewer)
- `omni.services.livestream.nvcf` — NVCF cloud streaming (used by `isaac-sim.streaming.sh`)
- `omni.kit.livestream.core` — low-level C++ binding (dependency, not used directly)

### 3. `isaac-sim.streaming.sh --exec scene.py` breaks physics-driven animation

`isaac-sim.streaming.sh` does open the correct WebRTC stack, but the `--exec` flag runs the script during Kit's startup sequence. Two things break:

- `timeline.play()` called at that point gets **reset** by Kit's own post-startup initialization — the simulation appears permanently paused.
- Character animation (`omni.anim.people`) requires the physics loop to be actively stepped. In exec mode Kit drives physics on its own schedule; the person idles instead of walking.

Deferring with `asyncio.ensure_future()` partially works for the timeline but is fragile. The standalone `SimulationApp` approach above avoids the problem entirely.

### 4. `SimulationApp(experience="isaacsim.exp.full.streaming.kit")` crashes immediately

The streaming kit app is designed to be launched via `kit/kit` binary, not driven by SimulationApp's Python update loop. Do not attempt this.

## Related Skills

- [write-isaac-sim-scene](../write-isaac-sim-scene) — Creating standalone Python scenes
