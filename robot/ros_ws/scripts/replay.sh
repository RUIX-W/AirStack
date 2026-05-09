#!/bin/bash

# Start recording images and bboxes
ros2 bag record \
  /robot_1/sensors/front_stereo/left/image_rect \
	  /robot_1/sensors/front_stereo/right/image_rect \
		  /robot_1/sensors/front_stereo/semantic_bbox2d \
			  /robot_1/sensors/front_stereo/semantic_bbox3d \
				  -o image_bbox_session &
					BAG_PID=$!

					# Activate TRACK mode
					ros2 topic pub --once /robot_1/behavior/keyboard_control_commanded_success std_msgs/Bool "data: true"
					sleep 1

					# Replay the trajectory — drone follows the same path
					ros2 bag play keyboard_traj --topics /robot_1/trajectory_controller/trajectory_override

					kill $BAG_PID
					ros2 topic pub --once /robot_1/behavior/keyboard_control_commanded_success std_msgs/Bool "data: false"
