---
name: run-system-tests
description: Run AirStack system tests. Use when verifying the full autonomy stack, checking Docker image builds, or running integration tests.
license: Apache-2.0
metadata:
  author: AirLab CMU
  repository: AirStack
---

# Skill: Run AirStack System Tests

## When to Use

Use this skill when you need to:

- Run Docker image build tests
- Verify the full stack comes up correctly
- Run integration tests against the autonomy stack

**Note:** This version of AirStack (0.14.4) has a `tests/` directory at the repo root. Check its contents for available tests before proceeding.

## Running Tests

### Via AirStack CLI

```bash
# Run all tests
airstack test -v

# Run specific test file
airstack test tests/test_<name>.py -v
```

### Manually Inside Container

```bash
# Start robot container without autolaunch
AUTOLAUNCH=false airstack up robot

# Build workspace
docker exec airstack-robot-1 bash -c "bws"

# Run ROS 2 tests
docker exec airstack-robot-1 bash -c "sws && colcon test --packages-select <package_name>"

# Show results
docker exec airstack-robot-1 bash -c "colcon test-result --verbose"
```

## Checking System Health

```bash
# Verify containers are running
airstack status

# Check all nodes are alive
docker exec airstack-robot-1 bash -c "ros2 node list"

# Check key topics are publishing
docker exec airstack-robot-1 bash -c "timeout 5 ros2 topic hz /robot_1/odometry"

# Check docker logs for errors
docker logs airstack-robot-1 2>&1 | grep -iE "error|fail|crash"
```

## Building and Verifying Docker Images

```bash
# Build all images
airstack image build

# Verify image builds
airstack images
```

## References

- `tests/` — system test directory (check for available tests)
- Related skills:
  - [test-in-simulation](../test-in-simulation) — end-to-end simulation testing
  - [debug-module](../debug-module) — diagnosing module issues
  - [use-airstack-cli](../use-airstack-cli) — CLI patterns for running commands
