#!/bin/bash

# Republish image_rect in lower frequency
ros2 run topic_tools throttle messages /robot_1/sensors/front_stereo/left/image_rect 5.0 /robot_1/sensors/front_stereo/left/image_rect_5hz &
THROTTLE_PID=$!
sleep 1

# Arm and takeoff — Python script mirrors the GUI button exactly:
# publishes BehaviorTreeCommands with Auto Takeoff Commanded=SUCCESS,
# all peer conditions=FAILURE, then blocks until takeoff_complete_success
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/auto_takeoff.py"

# take the first argument as output name
output_name=$1

# Start recording images and bboxes
ros2 bag record -s mcap \
  /robot_1/sensors/front_stereo/left/image_rect_5hz \
  /robot_1/sensors/front_stereo/semantic_bbox2d \
  /robot_1/sensors/front_stereo/semantic_bbox3d \
  -o $output_name &
BAG_PID=$!

# Activate keyboard control (TRACK mode)
ros2 topic pub --once /robot_1/behavior/keyboard_control_commanded_success std_msgs/Bool "data: true"
sleep 1

# Replay trajectory
ros2 bag play keyboard_traj --topics /robot_1/trajectory_controller/trajectory_override

# Done — stop recording and land
kill $BAG_PID $THROTTLE_PID
ros2 topic pub --once /robot_1/behavior/land_commanded_success std_msgs/Bool "data: true"
