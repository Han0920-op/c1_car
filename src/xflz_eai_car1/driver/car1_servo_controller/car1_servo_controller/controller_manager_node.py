#!/usr/bin/env python3
# encoding: utf-8
"""Controller manager node: orchestrates servo control for car1 robot arm and gripper."""
import math
import time
import threading
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from sensor_msgs.msg import JointState
from car1_servo_controller_msgs.msg import ServosPosition, ServoPosition, ServoState, ServoStateList
from car1_base_driver_msgs.srv import GetBusServoState
from car1_base_driver_msgs.msg import GetBusServoCmd
from car1_servo_controller.servo_manager import ServoManager
from car1_servo_controller.joint_position_controller import JointPositionController
from car1_servo_controller.joint_trajectory_controller import JointTrajectoryActionController


class ControllerManagerNode(Node):
    def __init__(self):
        super().__init__(
            'servo_controller',
            allow_undeclared_parameters=True,
            automatically_declare_parameters_from_overrides=True
        )

        # Parse joint configurations from parameters
        self.joint_controllers = {}
        self.connected_ids = {}
        joints_param = self.get_parameters_by_prefix('joints')

        # Group parameters by joint name
        joint_configs = {}
        for key, param in joints_param.items():
            parts = key.split('.')
            joint_name = parts[0]
            field = parts[1] if len(parts) > 1 else key
            if joint_name not in joint_configs:
                joint_configs[joint_name] = {}
            joint_configs[joint_name][field] = param.value

        # Create joint position controllers
        for joint_name, config in joint_configs.items():
            servo_id = int(config['id'])
            init_pos = int(config['init'])
            min_pos = int(config['min'])
            max_pos = int(config['max'])
            orientation = int(config['orientation'])

            self.get_logger().info(f'Loading joint {joint_name}: id={servo_id}, orientation={orientation}')

            controller = JointPositionController(
                joint_name, servo_id, init_pos, min_pos, max_pos, orientation
            )
            self.joint_controllers[joint_name] = controller
            self.connected_ids[str(servo_id)] = joint_name

        # Create servo manager
        self.servo_manager = ServoManager(self, self.connected_ids)

        # Create trajectory action controllers from config
        controllers_param = self.get_parameters_by_prefix('controllers')
        controller_configs = {}
        for key, param in controllers_param.items():
            parts = key.split('.')
            ctrl_name = parts[0]
            field = parts[1] if len(parts) > 1 else key
            if ctrl_name not in controller_configs:
                controller_configs[ctrl_name] = {}
            controller_configs[ctrl_name][field] = param.value

        self.trajectory_controllers = {}
        for ctrl_name, config in controller_configs.items():
            joint_names = config.get('joints', [])
            action_name = config.get('action_name', f'{ctrl_name}/follow_joint_trajectory')
            controllers = [self.joint_controllers[j] for j in joint_names]
            traj_ctrl = JointTrajectoryActionController(
                self, self.servo_manager, ctrl_name, action_name, controllers
            )
            self.trajectory_controllers[ctrl_name] = traj_ctrl

        # Publishers
        self.joint_states_pub = self.create_publisher(JointState, '/joint_states', 10)
        self.servo_states_pub = self.create_publisher(ServoStateList, '~/servo_states', 1)

        # Subscribers
        self.create_subscription(
            ServosPosition, 'servo_controller', self.servo_controller_callback, 1
        )
        self.create_subscription(
            JointState, 'joint_controller', self.joint_controller_callback, 1
        )

        # Wait for base driver to be ready
        namespace = self.get_namespace()
        if namespace == '/':
            namespace = ''
        self.init_client = self.create_client(
            Trigger, namespace + '/car1_base_driver/init_finish'
        )
        self.get_logger().info('Waiting for car1_base_driver/init_finish...')
        self.init_client.wait_for_service()
        self.get_logger().info('car1_base_driver ready.')

        # Create client for reading actual servo positions
        self.get_state_client = self.create_client(
            GetBusServoState, namespace + '/car1_base_driver/bus_servo/get_state'
        )

        # Cache for last known actual positions (fallback when readback fails)
        self.last_actual_positions = {}
        for joint_name, controller in self.joint_controllers.items():
            self.last_actual_positions[joint_name] = controller.initial_position_raw

        # Track in-flight read futures per joint to avoid stacking requests
        self.pending_read_futures = {}

        # Round-robin index for staggering servo reads across publish ticks
        self._read_cursor = 0

        # Publish joint states via main-thread timer (avoids cross-thread executor issues)
        publish_rate = self.get_parameter_or(
            'publish_rate', rclpy.parameter.Parameter('publish_rate', value=5.0)
        ).value
        self.publish_period = 1.0 / publish_rate
        self.publish_timer = self.create_timer(self.publish_period, self._publish_joint_states_tick)

        # Service: init_finish
        self.create_service(Trigger, '~/init_finish', self._init_finish_callback)
        self.get_logger().info('\033[1;32mservo_controller started\033[0m')

    def _init_finish_callback(self, request, response):
        response.success = True
        return response

    def servo_controller_callback(self, msg):
        """Handle servo position commands (pulse, rad, or deg units)."""
        positions = self.servo_manager.get_position()
        valid_positions = []

        if msg.position_unit == 'pulse':
            for p in msg.position:
                if str(p.id) in positions:
                    valid_positions.append(p)
            self.servo_manager.set_position(msg.duration, valid_positions)

        elif msg.position_unit == 'rad':
            for p in msg.position:
                if str(p.id) in positions:
                    joint_name = positions[str(p.id)].name
                    pulse = self.joint_controllers[joint_name].pos_rad_to_pulse(p.position)
                    servo_pos = ServoPosition()
                    servo_pos.id = p.id
                    servo_pos.position = float(pulse)
                    valid_positions.append(servo_pos)
            self.servo_manager.set_position(msg.duration, valid_positions)

        elif msg.position_unit == 'deg':
            for p in msg.position:
                if str(p.id) in positions:
                    joint_name = positions[str(p.id)].name
                    pulse = self.joint_controllers[joint_name].pos_rad_to_pulse(
                        math.radians(p.position)
                    )
                    servo_pos = ServoPosition()
                    servo_pos.id = p.id
                    servo_pos.position = float(pulse)
                    valid_positions.append(servo_pos)
            self.servo_manager.set_position(msg.duration, valid_positions)

    def joint_controller_callback(self, msg):
        """Handle JointState commands (radians)."""
        for name, position in zip(msg.name, msg.position):
            if name in self.joint_controllers:
                controller = self.joint_controllers[name]
                pulse = controller.pos_rad_to_pulse(position)
                servo_pos = ServoPosition()
                servo_pos.id = controller.servo_id
                servo_pos.position = float(pulse)
                self.servo_manager.set_position(0.02, [servo_pos])
                time.sleep(0.005)

    def _publish_joint_states_tick(self):
        """Timer callback (main thread): publish cached positions, kick off async readback."""
        # Kick off async read for one servo per tick (round-robin to avoid bus congestion)
        self._kick_off_one_read()

        # Publish current cache
        joint_msg = JointState()
        joint_msg.header.stamp = self.get_clock().now().to_msg()
        joint_msg.header.frame_id = 'base_link'

        servo_list_msg = ServoStateList()
        servo_list_msg.header = joint_msg.header

        for joint_name, controller in self.joint_controllers.items():
            pulse = self.last_actual_positions.get(joint_name, controller.initial_position_raw)

            joint_msg.name.append(joint_name)
            rad = controller.pos_pulse_to_rad(pulse)
            joint_msg.position.append(rad)

            servo_state = ServoState()
            servo_state.id = controller.servo_id
            servo_state.position = pulse
            servo_list_msg.servo_state.append(servo_state)

        self.joint_states_pub.publish(joint_msg)
        self.servo_states_pub.publish(servo_list_msg)

    def _kick_off_one_read(self):
        """Send one async read request per tick (round-robin), update cache via callback."""
        if not self.get_state_client.service_is_ready():
            return

        joint_names = list(self.joint_controllers.keys())
        if not joint_names:
            return

        # Round-robin: read one joint per tick
        joint_name = joint_names[self._read_cursor % len(joint_names)]
        self._read_cursor += 1

        # Skip if previous read for this joint hasn't returned yet
        prev = self.pending_read_futures.get(joint_name)
        if prev is not None and not prev.done():
            return

        controller = self.joint_controllers[joint_name]
        req = GetBusServoState.Request()
        cmd = GetBusServoCmd()
        cmd.id = controller.servo_id
        cmd.get_position = 1
        req.cmd = [cmd]

        future = self.get_state_client.call_async(req)
        self.pending_read_futures[joint_name] = future
        future.add_done_callback(lambda f, jn=joint_name: self._on_read_response(jn, f))

    def _on_read_response(self, joint_name, future):
        """Callback when get_state response arrives; update cache."""
        try:
            response = future.result()
            if response and response.success and response.state:
                state = response.state[0]
                if state.position and state.position[0] > 0:
                    self.last_actual_positions[joint_name] = state.position[0]
        except Exception:
            pass  # Keep stale cache value


def main(args=None):
    rclpy.init(args=args)
    node = ControllerManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
