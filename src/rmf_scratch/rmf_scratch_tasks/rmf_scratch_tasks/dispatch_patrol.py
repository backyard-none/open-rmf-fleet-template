#!/usr/bin/env python3
import sys
import uuid
import argparse
import json
import asyncio

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, QoSHistoryPolicy as History, QoSDurabilityPolicy as Durability, QoSReliabilityPolicy as Reliability
from rmf_task_msgs.msg import ApiRequest, ApiResponse

class ScratchTaskRequester(Node):
    def __init__(self, argv=sys.argv):
        super().__init__('scratch_task_requester')
        parser = argparse.ArgumentParser()
        parser.add_argument('-p', '--places', required=True, nargs='+', type=str, help='Gidilecek noktalar')
        parser.add_argument('-n', '--rounds', help='Kac tur atilacak', type=int, default=1)
        parser.add_argument("--use_sim_time", action="store_true", help='Simulasyon zamani kullan')
        self.args = parser.parse_args(argv[1:])
        
        self.response = asyncio.Future()

        transient_qos = QoSProfile(history=History.KEEP_LAST, depth=1, reliability=Reliability.RELIABLE, durability=Durability.TRANSIENT_LOCAL)
        self.pub = self.create_publisher(ApiRequest, 'task_api_requests', transient_qos)

        if self.args.use_sim_time:
            self.set_parameters([Parameter("use_sim_time", Parameter.Type.BOOL, True)])

        msg = ApiRequest()
        msg.request_id = "scratch_patrol_" + str(uuid.uuid4())
        
        payload = {
            "type": "dispatch_task_request",
            "request": {
                "unix_millis_earliest_start_time": int(self.get_clock().now().nanoseconds / 10**6),
                "category": "patrol",
                "description": {"places": self.args.places, "rounds": self.args.rounds}
            }
        }
        msg.json_msg = json.dumps(payload)

        def receive_response(response_msg: ApiResponse):
            if response_msg.request_id == msg.request_id:
                self.response.set_result(json.loads(response_msg.json_msg))

        transient_qos.depth = 10
        self.sub = self.create_subscription(ApiResponse, 'task_api_responses', receive_response, transient_qos)
        self.pub.publish(msg)
        self.get_logger().info(f"Patrol task s being dispatched: {self.args.places}")

def main(argv=sys.argv):
    rclpy.init(args=sys.argv)
    args_without_ros = rclpy.utilities.remove_ros_args(sys.argv)
    task_requester = ScratchTaskRequester(args_without_ros)
    
    rclpy.spin_until_future_complete(task_requester, task_requester.response, timeout_sec=5.0)
    
    if task_requester.response.done():
        print(f'answered:\n{json.dumps(task_requester.response.result(), indent=2)}')
    else:
        print('unanswered:(')
        
    rclpy.shutdown()

if __name__ == '__main__':
    main(sys.argv)