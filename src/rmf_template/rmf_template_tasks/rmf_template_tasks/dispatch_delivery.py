#!/usr/bin/env python3
# Dispatch a delivery task to the robot fleet

import sys
import argparse
import json
import uuid
import time
import rclpy
from rclpy.node import Node
from rmf_task_msgs.msg import ApiRequest


def main(argv=sys.argv):
    parser = argparse.ArgumentParser(description='Dispatch delivery task')
    parser.add_argument('-p', '--pickup',  required=True, help='Pickup waypoint')
    parser.add_argument('-d', '--dropoff', required=True, help='Dropoff waypoint')
    parser.add_argument('--use_sim_time', action='store_true')
    args = parser.parse_args(argv[1:])

    rclpy.init()
    node = Node('delivery_dispatcher')
    pub = node.create_publisher(ApiRequest, '/task_api_requests', 10)

    msg = ApiRequest()
    msg.request_id = f'delivery_{uuid.uuid4().hex[:8]}'
    msg.json_msg = json.dumps({
        'type': 'dispatch_task_request',
        'request': {
            'category': 'delivery',
            'description': {
                'pickup':  {'place': args.pickup},
                'dropoff': {'place': args.dropoff}
            }
        }
    })

    time.sleep(1.0)
    pub.publish(msg)
    print(f'Delivery dispatched: {args.pickup} → {args.dropoff}')
    print(f'Request ID: {msg.request_id}')

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
