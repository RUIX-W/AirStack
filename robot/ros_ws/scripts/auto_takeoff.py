#!/usr/bin/env python3
"""
Triggers auto takeoff via the behavior tree, then waits for completion.
Mirrors the GUI 'Arm and Takeoff' button: publishes BehaviorTreeCommands with
Auto Takeoff Commanded=SUCCESS and all peer conditions=FAILURE, then waits for
the takeoff_complete_success topic to confirm.
"""
import sys
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from behavior_tree_msgs.msg import BehaviorTreeCommand, BehaviorTreeCommands, Status

# All condition names from the GUI config (gui_config.yaml)
ALL_CONDITIONS = [
    'Auto Takeoff Commanded',
    'Fixed Trajectory Commanded',
    'Global Plan Commanded',
    'Pause Commanded',
    'Rewind Commanded',
    'Disarm Commanded',
    'Land Commanded',
    'Autonomously Explore Commanded',
    'Keyboard Control Commanded',
    'Target Tracking Commanded',
]

ROBOT_NS = sys.argv[1] if len(sys.argv) > 1 else 'robot_1'


class AutoTakeoff(Node):
    def __init__(self):
        super().__init__('auto_takeoff')
        self.done = False

        self.cmd_pub = self.create_publisher(
            BehaviorTreeCommands,
            f'/{ROBOT_NS}/behavior/behavior_tree_commands',
            10,
        )
        self.create_subscription(
            Bool,
            f'/{ROBOT_NS}/behavior/takeoff_complete_success',
            self._on_takeoff_complete,
            10,
        )

        # Give the publisher time to connect, then send the command
        self.create_timer(0.5, self._send_command)

    def _send_command(self):
        msg = BehaviorTreeCommands()
        for name in ALL_CONDITIONS:
            cmd = BehaviorTreeCommand()
            cmd.condition_name = name
            cmd.status = Status.SUCCESS if name == 'Auto Takeoff Commanded' else Status.FAILURE
            msg.commands.append(cmd)
        self.cmd_pub.publish(msg)
        self.get_logger().info('Published Auto Takeoff Commanded = SUCCESS')

    def _on_takeoff_complete(self, msg: Bool):
        if msg.data:
            self.get_logger().info('Takeoff complete')
            # Clear the auto takeoff condition so it does not interfere with
            # whatever behavior follows
            clear = BehaviorTreeCommands()
            for name in ALL_CONDITIONS:
                cmd = BehaviorTreeCommand()
                cmd.condition_name = name
                cmd.status = Status.FAILURE
                clear.commands.append(cmd)
            self.cmd_pub.publish(clear)
            self.done = True


def main():
    rclpy.init()
    node = AutoTakeoff()
    while rclpy.ok() and not node.done:
        rclpy.spin_once(node, timeout_sec=0.1)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
