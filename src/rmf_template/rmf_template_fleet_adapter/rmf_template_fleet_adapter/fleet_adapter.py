# My Robot Fleet - Fleet Adapter
# This is the main entry point that connects your robot fleet to RMF.

import sys
import argparse
import yaml
import time
import threading
import datetime

import rclpy
import rclpy.node
from rclpy.parameter import Parameter

import rmf_adapter as adpt
import rmf_adapter.vehicletraits as traits
import rmf_adapter.battery as battery
import rmf_adapter.geometry as geometry
import rmf_adapter.graph as graph
import rmf_adapter.plan as plan

from rmf_task_msgs.msg import TaskProfile, TaskType
from rmf_fleet_msgs.msg import LaneRequest, ClosedLanes

from functools import partial
from rclpy.qos import QoSProfile
from rclpy.qos import QoSHistoryPolicy as History
from rclpy.qos import QoSDurabilityPolicy as Durability
from rclpy.qos import QoSReliabilityPolicy as Reliability
from rclpy.qos import qos_profile_system_default

from .RobotClientAPI import RobotAPI
from .RobotCommandHandle import RobotCommandHandle


def initialize_fleet(config_yaml, nav_graph_path, node, use_sim_time):

    fleet_config = config_yaml['rmf_fleet']

    # ------------------------------------------------------------------
    # 1) Vehicle profile (footprint and speed limits)
    # TODO: Adjust footprint and vicinity radius for your robot (metres)
    # ------------------------------------------------------------------
    profile = traits.Profile(
        geometry.make_final_convex_circle(fleet_config['profile']['footprint']),
        geometry.make_final_convex_circle(fleet_config['profile']['vicinity']))

    vehicle_traits = traits.VehicleTraits(
        linear=traits.Limits(*fleet_config['limits']['linear']),
        angular=traits.Limits(*fleet_config['limits']['angular']),
        profile=profile)
    vehicle_traits.differential.reversible = fleet_config['reversible']

    # ------------------------------------------------------------------
    # 2) Battery system
    # TODO: Fill in your robot's battery specs in config.yaml
    # ------------------------------------------------------------------
    battery_sys = battery.BatterySystem.make(
        fleet_config['battery_system']['voltage'],
        fleet_config['battery_system']['capacity'],
        fleet_config['battery_system']['charging_current'])

    mech_sys = battery.MechanicalSystem.make(
        fleet_config['mechanical_system']['mass'],
        fleet_config['mechanical_system']['moment_of_inertia'],
        fleet_config['mechanical_system']['friction_coefficient'])

    motion_sink = battery.SimpleMotionPowerSink(battery_sys, mech_sys)
    ambient_sink = battery.SimpleDevicePowerSink(
        battery_sys,
        battery.PowerSystem.make(fleet_config['ambient_system']['power']))
    tool_sink = battery.SimpleDevicePowerSink(
        battery_sys,
        battery.PowerSystem.make(fleet_config['tool_system']['power']))

    # ------------------------------------------------------------------
    # 3) Navigation graph
    # This is the map of waypoints and lanes your robot can travel on.
    # ------------------------------------------------------------------
    nav_graph = graph.parse_graph(nav_graph_path, vehicle_traits)

    # ------------------------------------------------------------------
    # 4) Create the RMF fleet adapter
    # ------------------------------------------------------------------
    fleet_name = fleet_config['name']
    adapter = adpt.Adapter.make(f'{fleet_name}_fleet_adapter')
    assert adapter, 'Could not create adapter. Is the RMF Schedule node running?'

    if use_sim_time:
        adapter.node.use_sim_time()
    adapter.start()
    time.sleep(1.0)

    node.declare_parameter('server_uri', rclpy.Parameter.Type.STRING)
    server_uri = node.get_parameter('server_uri').get_parameter_value().string_value
    if server_uri == '':
        server_uri = None

    fleet_handle = adapter.add_fleet(
        fleet_name, vehicle_traits, nav_graph, server_uri)

    fleet_handle.fleet_state_publish_period(
        datetime.timedelta(
            seconds=1.0 / fleet_config['publish_fleet_state']))

    # ------------------------------------------------------------------
    # 5) Task planner settings
    # ------------------------------------------------------------------
    ok = fleet_handle.set_task_planner_params(
        battery_sys,
        motion_sink,
        ambient_sink,
        tool_sink,
        fleet_config['recharge_threshold'],
        fleet_config['recharge_soc'],
        fleet_config['account_for_battery_drain'],
        fleet_config['task_capabilities']['finishing_request'])
    assert ok, 'Failed to set task planner params'

    # ------------------------------------------------------------------
    # 6) Task capabilities
    # TODO: Enable only the task types your robot supports
    # ------------------------------------------------------------------
    task_capabilities = []
    if fleet_config['task_capabilities']['loop']:
        task_capabilities.append(TaskType.TYPE_LOOP)
    if fleet_config['task_capabilities']['delivery']:
        task_capabilities.append(TaskType.TYPE_DELIVERY)
    if fleet_config['task_capabilities']['clean']:
        task_capabilities.append(TaskType.TYPE_CLEAN)

    def _task_request_check(task_capabilities, msg: TaskProfile):
        return msg.description.task_type in task_capabilities

    fleet_handle.accept_task_requests(
        partial(_task_request_check, task_capabilities))

    # TODO: Add any custom actions your robot can perform
    # Example: 'mine', 'load', 'unload'
    def _consider(description: dict):
        confirm = adpt.fleet_update_handle.Confirmation()
        confirm.accept()
        return confirm

    fleet_handle.add_performable_action('teleop', _consider)

    # ------------------------------------------------------------------
    # 7) Robot update handle inserter
    # ------------------------------------------------------------------
    def _updater_inserter(cmd_handle, update_handle):
        cmd_handle.update_handle = update_handle

        def _action_executor(category, description, execution):
            with cmd_handle._lock:
                if len(description) > 0 and \
                        description in cmd_handle.graph.keys:
                    cmd_handle.action_waypoint_index = \
                        cmd_handle.find_waypoint(description).index
                else:
                    cmd_handle.action_waypoint_index = \
                        cmd_handle.last_known_waypoint_index
                cmd_handle.on_waypoint = None
                cmd_handle.on_lane = None
                cmd_handle.action_execution = execution

        cmd_handle.update_handle.set_action_executor(_action_executor)

        if 'max_delay' in cmd_handle.config:
            cmd_handle.update_handle.set_maximum_delay(
                cmd_handle.config['max_delay'])

        if cmd_handle.charger_waypoint_index < cmd_handle.graph.num_waypoints:
            cmd_handle.update_handle.set_charger_waypoint(
                cmd_handle.charger_waypoint_index)

    # ------------------------------------------------------------------
    # 8) Connect to your robot's Fleet Manager HTTP API
    # TODO: Make sure fleet_manager is running and reachable at this address
    # ------------------------------------------------------------------
    prefix = 'http://' + fleet_config['fleet_manager']['ip'] + \
             ':' + str(fleet_config['fleet_manager']['port'])
    api = RobotAPI(
        prefix,
        fleet_config['fleet_manager']['user'],
        fleet_config['fleet_manager']['password'])

    # ------------------------------------------------------------------
    # 9) Add robots to the fleet
    # ------------------------------------------------------------------
    robots = {}
    missing_robots = config_yaml['robots']

    def _add_fleet_robots():
        while len(missing_robots) > 0:
            time.sleep(0.2)
            for robot_name in list(missing_robots.keys()):
                node.get_logger().debug(f'Connecting to robot: {robot_name}')
                data = api.data(robot_name)
                if data is None or not data['success']:
                    continue

                node.get_logger().info(f'Initializing robot: {robot_name}')
                robots_config = config_yaml['robots'][robot_name]
                rmf_config = robots_config['rmf_config']
                robot_config = robots_config['robot_config']

                initial_waypoint = rmf_config['start']['waypoint']
                initial_orientation = data['data']['position'].get(
                    'yaw', rmf_config['start']['orientation'])

                time_now = adapter.now()
                position = api.position(robot_name)
                if position is None:
                    node.get_logger().info(
                        f'Failed to get position of {robot_name}, retrying...')
                    continue

                if initial_waypoint and initial_orientation is not None:
                    initial_waypoint_index = nav_graph.find_waypoint(
                        initial_waypoint).index
                    starts = [plan.Start(
                        time_now, initial_waypoint_index, initial_orientation)]
                else:
                    starts = plan.compute_plan_starts(
                        nav_graph,
                        rmf_config['start']['map_name'],
                        position,
                        time_now)

                if not starts:
                    node.get_logger().error(
                        f'Cannot determine start position for {robot_name}')
                    continue

                robot = RobotCommandHandle(
                    name=robot_name,
                    fleet_name=fleet_name,
                    config=robot_config,
                    node=node,
                    graph=nav_graph,
                    vehicle_traits=vehicle_traits,
                    map_name=rmf_config['start']['map_name'],
                    start=starts[0],
                    position=position,
                    charger_waypoint=rmf_config['charger']['waypoint'],
                    update_frequency=rmf_config.get(
                        'robot_state_update_frequency', 1),
                    lane_merge_distance=fleet_config.get(
                        'lane_merge_distance', 0.1),
                    adapter=adapter,
                    api=api)

                if robot.initialized:
                    robots[robot_name] = robot
                    fleet_handle.add_robot(
                        robot,
                        robot_name,
                        profile,
                        [starts[0]],
                        partial(_updater_inserter, robot))
                    node.get_logger().info(
                        f'Successfully added robot: {robot_name}')
                else:
                    node.get_logger().error(
                        f'Failed to initialize robot: {robot_name}')

                del missing_robots[robot_name]

    threading.Thread(target=_add_fleet_robots, daemon=True).start()

    # ------------------------------------------------------------------
    # 10) Lane closure handling
    # ------------------------------------------------------------------
    closed_lanes = []

    transient_qos = QoSProfile(
        history=History.KEEP_LAST,
        depth=1,
        reliability=Reliability.RELIABLE,
        durability=Durability.TRANSIENT_LOCAL)

    closed_lanes_pub = node.create_publisher(
        ClosedLanes, 'closed_lanes', qos_profile=transient_qos)

    def _lane_request_cb(msg):
        if msg.fleet_name != fleet_name:
            return
        fleet_handle.open_lanes(msg.open_lanes)
        fleet_handle.close_lanes(msg.close_lanes)
        for idx in msg.close_lanes:
            if idx not in closed_lanes:
                closed_lanes.append(idx)
        for idx in msg.open_lanes:
            if idx in closed_lanes:
                closed_lanes.remove(idx)
        for robot in robots.values():
            robot.newly_closed_lanes(msg.close_lanes)
        state_msg = ClosedLanes()
        state_msg.fleet_name = fleet_name
        state_msg.closed_lanes = closed_lanes
        closed_lanes_pub.publish(state_msg)

    node.create_subscription(
        LaneRequest, 'lane_closure_requests',
        _lane_request_cb, qos_profile=qos_profile_system_default)

    return adapter


def main(argv=sys.argv):
    rclpy.init(args=argv)
    adpt.init_rclcpp()
    args_without_ros = rclpy.utilities.remove_ros_args(argv)

    parser = argparse.ArgumentParser(
        prog='fleet_adapter',
        description='My Robot Fleet Adapter for RMF')
    parser.add_argument('-c', '--config_file', type=str, required=True,
                        help='Path to config.yaml')
    parser.add_argument('-n', '--nav_graph', type=str, required=True,
                        help='Path to nav_graph.yaml')
    parser.add_argument('-sim', '--use_sim_time', action='store_true',
                        help='Use simulation time (default: false)')
    args = parser.parse_args(args_without_ros[1:])

    with open(args.config_file, 'r') as f:
        config_yaml = yaml.safe_load(f)

    fleet_name = config_yaml['rmf_fleet']['name']
    node = rclpy.node.Node(f'{fleet_name}_command_handle')

    if args.use_sim_time:
        node.set_parameters([Parameter('use_sim_time',
                                       Parameter.Type.BOOL, True)])

    adapter = initialize_fleet(
        config_yaml, args.nav_graph, node, args.use_sim_time)

    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(node)
    executor.spin()

    node.destroy_node()
    executor.shutdown()
    rclpy.shutdown()


if __name__ == '__main__':
    main(sys.argv)
