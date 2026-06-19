#!/usr/bin/env python3
# Dispatch a patrol task to the robot fleet

import sys
import argparse
import json
import uuid
import time
import rclpy
from rclpy.node import Node
from rmf_task_msgs.msg import ApiRequest


def main(argv=sys.argv):
    parser = argparse.ArgumentParser(description='Dispatch patrol task')
    parser.add_argument('-s', '--start',  required=True, help='Start waypoint')
    parser.add_argument('-f', '--finish', required=True, help='Finish waypoint')
    parser.add_argument('-n', '--loops',  type=int, default=1, help='Number of loops')
    parser.add_argument('--use_sim_time', action='store_true')
    args = parser.parse_args(argv[1:])

    rclpy.init()
    node = Node('patrol_dispatcher')
    pub = node.create_publisher(ApiRequest, '/task_api_requests', 10)

    msg = ApiRequest()
    msg.request_id = f'patrol_{uuid.uuid4().hex[:8]}'
    msg.json_msg = json.dumps({
        'type': 'dispatch_task_request',
        'request': {
            'category': 'patrol',
            'description': {
                'places': [args.start, args.finish],
                'rounds': args.loops
            }
        }
    })

    time.sleep(1.0)
    pub.publish(msg)
    print(f'Patrol dispatched: {args.start} → {args.finish} x{args.loops}')
    print(f'Request ID: {msg.request_id}')

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
