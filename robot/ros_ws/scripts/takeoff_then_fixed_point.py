#!/usr/bin/env python3
"""Send the same takeoff and fixed-point task actions used by the RViz panel."""

import argparse
import sys
import time

import rclpy
from action_msgs.msg import GoalStatus
from airstack_msgs.msg import FixedTrajectory
from diagnostic_msgs.msg import KeyValue
from rclpy.action import ActionClient
from rclpy.node import Node
from task_msgs.action import FixedTrajectoryTask, TakeoffTask


STATUS_NAMES = {
    GoalStatus.STATUS_UNKNOWN: "UNKNOWN",
    GoalStatus.STATUS_ACCEPTED: "ACCEPTED",
    GoalStatus.STATUS_EXECUTING: "EXECUTING",
    GoalStatus.STATUS_CANCELING: "CANCELING",
    GoalStatus.STATUS_SUCCEEDED: "SUCCEEDED",
    GoalStatus.STATUS_CANCELED: "CANCELED",
    GoalStatus.STATUS_ABORTED: "ABORTED",
}


def normalize_robot_name(robot_name: str) -> str:
    return robot_name.strip("/")


def action_name(robot_name: str, suffix: str) -> str:
    return f"/{normalize_robot_name(robot_name)}/tasks/{suffix}"


def spin_until(node: Node, future, timeout_s: float, description: str) -> bool:
    deadline = time.monotonic() + timeout_s
    while rclpy.ok() and not future.done():
        rclpy.spin_once(node, timeout_sec=0.1)
        if time.monotonic() > deadline:
            node.get_logger().error(f"Timed out while waiting for {description}")
            return False
    return future.done()


def send_action_goal(node: Node, client, goal, timeout_s: float, label: str):
    if not client.wait_for_server(timeout_sec=10.0):
        node.get_logger().error(f"{label} action server is not available")
        return False

    def feedback_callback(feedback_msg):
        fb = feedback_msg.feedback
        if hasattr(fb, "current_altitude_m"):
            node.get_logger().info(
                f"{label} feedback: {fb.status} "
                f"alt={fb.current_altitude_m:.2f}/{fb.target_altitude_m:.2f} m"
            )
        elif hasattr(fb, "current_position"):
            p = fb.current_position
            node.get_logger().info(
                f"{label} feedback: {fb.status} progress={fb.progress:.2f} "
                f"pos=({p.x:.2f}, {p.y:.2f}, {p.z:.2f})"
            )

    node.get_logger().info(f"Sending {label} goal")
    goal_future = client.send_goal_async(goal, feedback_callback=feedback_callback)
    if not spin_until(node, goal_future, timeout_s, f"{label} goal acceptance"):
        return False

    goal_handle = goal_future.result()
    if goal_handle is None or not goal_handle.accepted:
        node.get_logger().error(f"{label} goal was rejected")
        return False

    result_future = goal_handle.get_result_async()
    if not spin_until(node, result_future, timeout_s, f"{label} result"):
        return False

    wrapped = result_future.result()
    result = wrapped.result
    status_name = STATUS_NAMES.get(wrapped.status, str(wrapped.status))
    success = bool(getattr(result, "success", False)) and wrapped.status == GoalStatus.STATUS_SUCCEEDED
    message = getattr(result, "message", "")
    node.get_logger().info(f"{label} result: status={status_name} success={success} message={message!r}")
    return success


def fixed_point_goal(args) -> FixedTrajectoryTask.Goal:
    spec = FixedTrajectory()
    spec.type = "Point"
    values = {
        "frame_id": args.point_frame,
        "velocity": args.point_velocity,
        "max_acceleration": args.point_max_acceleration,
        "x": args.point_x,
        "y": args.point_y,
        "height": args.point_height,
    }
    spec.attributes = [KeyValue(key=key, value=str(value)) for key, value in values.items()]

    goal = FixedTrajectoryTask.Goal()
    goal.trajectory_spec = spec
    goal.loop = args.loop
    return goal


def parse_args():
    parser = argparse.ArgumentParser(
        description="Take off, then send a fixed Point trajectory through AirStack task actions."
    )
    parser.add_argument("--robot", default="/robot_1", help="Robot namespace, e.g. /robot_1")
    parser.add_argument("--skip-takeoff", action="store_true", help="Only send the fixed trajectory")
    parser.add_argument("--takeoff-altitude", type=float, default=2.0)
    parser.add_argument("--takeoff-velocity", type=float, default=1.0)
    parser.add_argument("--takeoff-timeout", type=float, default=120.0)
    parser.add_argument("--wait-after-takeoff", type=float, default=0.0)

    parser.add_argument("--point-frame", default="base_link")
    parser.add_argument("--point-x", type=float, default=0.0)
    parser.add_argument("--point-y", type=float, default=3.0)
    parser.add_argument("--point-height", type=float, default=0.0)
    parser.add_argument("--point-velocity", type=float, default=1.0)
    parser.add_argument("--point-max-acceleration", type=float, default=1.0)
    parser.add_argument("--fixed-timeout", type=float, default=120.0)
    parser.add_argument("--loop", action="store_true", help="Repeat fixed trajectory until canceled")
    return parser.parse_args()


def main():
    args = parse_args()
    rclpy.init()
    node = Node("takeoff_then_fixed_point_client")

    try:
        takeoff_client = ActionClient(node, TakeoffTask, action_name(args.robot, "takeoff"))
        fixed_client = ActionClient(node, FixedTrajectoryTask, action_name(args.robot, "fixed_trajectory"))

        if not args.skip_takeoff:
            takeoff_goal = TakeoffTask.Goal()
            takeoff_goal.target_altitude_m = float(args.takeoff_altitude)
            takeoff_goal.velocity_m_s = float(args.takeoff_velocity)
            if not send_action_goal(node, takeoff_client, takeoff_goal, args.takeoff_timeout, "takeoff"):
                return 1
            if args.wait_after_takeoff > 0.0:
                node.get_logger().info(f"Waiting {args.wait_after_takeoff:.1f}s after takeoff")
                time.sleep(args.wait_after_takeoff)

        fixed_goal = fixed_point_goal(args)
        if not send_action_goal(node, fixed_client, fixed_goal, args.fixed_timeout, "fixed_point"):
            return 1

        return 0
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
