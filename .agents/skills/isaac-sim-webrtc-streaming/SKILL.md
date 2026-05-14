---
name: isaac-sim-webrtc-streaming
description: Enable browser-based WebRTC streaming for a standalone Isaac Sim Python scene. Use when you need the isaac-sim-webrtc Docker service to run a custom Python script (instead of a USD file) and stream it to the browser viewer on port 8210.
license: Apache-2.0
metadata:
  author: AirLab CMU
  repository: AirStack
---

# Skill: Isaac Sim WebRTC Browser Streaming

## When to Use

You need a standalone Python scene (e.g. `scene_with_walking_person.py`) to run
inside the `isaac-sim-webrtc` Docker service and be viewable in the browser at
`http://<host>:8210`.

## Architecture Overview

Three pieces must align for browser streaming to work:

```
isaac-sim-webrtc container
  └── run_isaac_python scene.py        ← drives physics, calls enable_extension()
        └── omni.kit.livestream.webrtc  ← WebRTC signaling on port 49100
                                           WebRTC media  on port 47998

isaac-sim-webrtc-viewer container
  └── vite preview (port 8210)         ← browser UI baked with signalingPort=49100
        └── connects to → port 49100
```

The viewer image has ports **baked in at build time** from `docker-compose.yaml`
build args (`ISAAC_SIM_WEBRTC_SIGNAL_PORT`, `ISAAC_SIM_WEBRTC_STREAM_PORT`).
Changing ports at runtime has no effect — you would need to rebuild the image.

## The One Rule: Use `enable_extension`, Not `livestream=2`

The only correct way to enable WebRTC streaming from a standalone Python script
in Isaac Sim 5.1 is:

```python
from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": True, "hide_ui": False})

from isaacsim.core.utils.extensions import enable_extension
simulation_app.set_setting("/app/window/drawMouse", True)
enable_extension("omni.kit.livestream.webrtc")
```

The `omni.kit.livestream.webrtc` extension defaults to **port 49100**, which is
exactly what the browser viewer expects. This is documented in the official NVIDIA
example at:

```
/isaac-sim/AirStack/simulation/isaac-sim/standalone_examples/api/isaacsim.simulation_app/livestream.py
```

After this, run your normal standalone physics loop — `world.step(render=True)`
drives physics AND streaming simultaneously.

## What Does NOT Work (and Why)

### `SimulationApp({"livestream": 2})`

This is a **no-op** in Isaac Sim 5.1. The `"livestream"` key is not in
`SimulationApp.DEFAULT_LAUNCHER_CONFIG` and is silently ignored — no streaming
extension is loaded and no port is opened. It was a valid parameter in older Isaac
Sim versions (2022/2023) that loaded `omni.kit.livestream.websocket`, but that
extension no longer exists in 5.1. Passing it gives false confidence that
streaming is active when it isn't.

### `isaac-sim.streaming.sh --exec scene.py`

`isaac-sim.streaming.sh` does open the correct WebRTC stack (port 49100) but via
a different Kit app (`isaacsim.exp.full.streaming.kit`). The `--exec` flag runs
the Python script inside an already-running Kit instance during its startup
sequence. This causes two hard problems:

1. **Timeline reset** — calling `timeline.play()` during `--exec` startup gets
   reset by Kit's own post-startup initialization. The simulation appears paused.
2. **Animation not driven** — character animation (e.g. `omni.anim.people`) needs
   the physics loop to be actively stepped. In exec mode, Kit drives physics on its
   own schedule; calling `world.step()` from inside an update callback causes
   double-stepping and the person idles instead of walking.

Deferring setup via `asyncio.ensure_future()` partially works for the timeline but
is fragile and unreliable across Isaac Sim versions.

### `SimulationApp({}, experience="isaacsim.exp.full.streaming.kit")`

This crashes immediately. The streaming kit app is designed to be launched via
`kit/kit` binary, not driven by SimulationApp's Python update loop.

## Step-by-Step: Add Streaming to a Script

### 1. Detect headless mode from environment

The `isaac-sim-webrtc` service already sets `ISAAC_SIM_HEADLESS=true` in its
`environment:` block. Read it in your script:

```python
import os
from isaacsim import SimulationApp

_HEADLESS = os.environ.get("ISAAC_SIM_HEADLESS", "false").lower() == "true"
simulation_app = SimulationApp({"headless": _HEADLESS, "hide_ui": False})

from isaacsim.core.utils.extensions import enable_extension

if _HEADLESS:
    simulation_app.set_setting("/app/window/drawMouse", True)
    enable_extension("omni.kit.livestream.webrtc")
```

This keeps the script usable in GUI mode (`ISAAC_SIM_HEADLESS=false`) and
headless streaming mode (`ISAAC_SIM_HEADLESS=true`) without any code changes.

### 2. Keep the normal standalone physics loop

Do not change the run loop. `world.step(render=True)` works identically for
display and streaming:

```python
def run(self):
    self.timeline.play()
    while simulation_app.is_running():
        world = World.instance()
        if world is not None and hasattr(world, "_scene"):
            world.step(render=True)
        else:
            omni.kit.app.get_app().update()
    self.timeline.stop()
    simulation_app.close()
```

### 3. Use `run_isaac_python` in `docker-compose.yaml`

In `simulation/isaac-sim/docker/docker-compose.yaml`, the standalone branch of
the `isaac-sim-webrtc` service command must use `run_isaac_python` (not
`isaac-sim.streaming.sh`):

```yaml
if [ "${ISAAC_SIM_USE_STANDALONE}" = 'true' ]; then
  tmux send-keys -t isaac "run_isaac_python /isaac-sim/AirStack/simulation/isaac-sim/launch_scripts/${ISAAC_SIM_SCRIPT_NAME} --ext-folder ~/.local/share/ov/data/documents/Kit/shared/exts" ENTER;
else
  tmux send-keys -t isaac "source /isaac-sim/jazzy_ws/install/setup.bash && ros2 launch isaacsim run_isaacsim.launch.py ..." ENTER;
fi;
```

`run_isaac_python` is a shell function defined in
`simulation/isaac-sim/docker/.bashrc` that runs `/isaac-sim/python.sh` with the
correct `PYTHONPATH` (ROS 3.12 paths stripped out to prevent conflicts).

### 4. Recreate the container

`docker compose restart` does NOT re-read the compose file. Always use:

```bash
docker compose -f simulation/isaac-sim/docker/docker-compose.yaml --env-file .env \
  up -d --force-recreate isaac-sim-webrtc
```

Or stop/remove/start if the viewer container name conflicts:

```bash
docker stop isaac-sim-webrtc isaac-sim-webrtc-viewer
docker rm   isaac-sim-webrtc isaac-sim-webrtc-viewer
docker compose -f simulation/isaac-sim/docker/docker-compose.yaml --env-file .env \
  up -d isaac-sim-webrtc
```

### 5. Verify

```bash
# Port 49100 should appear once the webrtc extension loads (~60-90 s after start)
netstat -tlnp | grep 49100

# Watch the scene setup in the tmux session inside the container
docker exec isaac-sim-webrtc bash -c "tmux capture-pane -t isaac -p | tail -20"

# Open browser
http://localhost:8210
```

## `.env` Configuration Reference

```bash
ISAAC_SIM_USE_STANDALONE="true"           # must be true to use a Python script
ISAAC_SIM_SCRIPT_NAME="scene_with_walking_person.py"
ISAAC_SIM_HEADLESS="true"                 # picked up by the script to enable WebRTC
ISAAC_SIM_WEBRTC_SIGNAL_PORT=49100        # default; baked into viewer image at build
ISAAC_SIM_WEBRTC_STREAM_PORT=47998        # default; baked into viewer image at build
```

## Port Reference

| Port  | What                          | Who sets it                          |
|-------|-------------------------------|--------------------------------------|
| 49100 | WebRTC signaling (WebSocket)  | `omni.kit.livestream.webrtc` default |
| 47998 | WebRTC media stream           | `omni.kit.livestream.webrtc` default |
| 8210  | Browser viewer UI             | `isaac-sim-webrtc-viewer` container  |

## Related Skills

- [write-isaac-sim-scene](../write-isaac-sim-scene) — Creating standalone Python scenes
- [use-airstack-cli](../use-airstack-cli) — Managing Docker containers with the airstack CLI
