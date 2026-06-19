# Robot Fleet - RobotClientAPI Template
# Fill in the TODO sections with your robot's API calls

import requests
from urllib.error import HTTPError


class RobotAPI:
    def __init__(self, prefix: str, user: str, password: str):
        self.prefix = prefix
        self.user = user
        self.password = password
        self.timeout = 5.0
        self.debug = False

    def position(self, robot_name: str):
        """Return robot position as [x, y, theta] in metres and radians.
        Return None if any error occurs."""
        response = self.data(robot_name)
        if response and response['success']:
            pos = response['data']['position']
            return [pos['x'], pos['y'], pos['yaw']]
        return None

    def navigate(self, robot_name: str, cmd_id: int,
                 pose, map_name: str, speed_limit=0.0):
        """Send a navigation command to the robot.
        Return True if robot accepted the request, else False."""
        # TODO: Replace with your robot's navigation endpoint
        url = self.prefix + f'/navigate?robot={robot_name}&cmd={cmd_id}'
        data = {
            'x': pose[0],
            'y': pose[1],
            'yaw': pose[2],
            'map': map_name,
            'speed_limit': speed_limit
        }
        try:
            r = requests.post(url, json=data, timeout=self.timeout)
            r.raise_for_status()
            if self.debug:
                print(f'Response: {r.json()}')
            return r.json()['success']
        except HTTPError as e:
            print(f'HTTP error: {e}')
        except Exception as e:
            print(f'Other error: {e}')
        return False

    def stop(self, robot_name: str, cmd_id: int):
        """Command the robot to stop.
        Return True if successful, else False."""
        # TODO: Replace with your robot's stop endpoint
        url = self.prefix + f'/stop?robot={robot_name}&cmd={cmd_id}'
        try:
            r = requests.get(url, timeout=self.timeout)
            r.raise_for_status()
            if self.debug:
                print(f'Response: {r.json()}')
            return r.json()['success']
        except HTTPError as e:
            print(f'HTTP error: {e}')
        except Exception as e:
            print(f'Other error: {e}')
        return False

    def navigation_completed(self, robot_name: str, cmd_id: int):
        """Return True if the robot has reached its destination
        for the given cmd_id, else False."""
        response = self.data(robot_name)
        if response and response.get('data'):
            return response['data']['last_completed_request'] == cmd_id
        return False

    def navigation_remaining_duration(self, robot_name: str, cmd_id: int):
        """Return the number of seconds remaining to reach the destination.
        Return None if unavailable."""
        response = self.data(robot_name)
        if response:
            arrival = response['data'].get('destination_arrival')
            if arrival and arrival.get('cmd_id') == cmd_id:
                return arrival.get('duration')
        return None

    def battery_soc(self, robot_name: str):
        """Return battery state of charge as a value between 0.0 and 1.0.
        Return None if any error occurs."""
        response = self.data(robot_name)
        if response and response.get('data'):
            return response['data']['battery'] / 100.0
        return None

    def start_process(self, robot_name: str, cmd_id: int,
                      process: str, map_name: str):
        """Request the robot to begin a custom process
        (e.g. loading, unloading, mining).
        Return True if accepted, else False."""
        # TODO: Replace with your robot's process endpoint
        url = self.prefix + f'/process?robot={robot_name}&cmd={cmd_id}'
        data = {'task': process, 'map': map_name}
        try:
            r = requests.post(url, json=data, timeout=self.timeout)
            r.raise_for_status()
            if self.debug:
                print(f'Response: {r.json()}')
            return r.json()['success']
        except HTTPError as e:
            print(f'HTTP error: {e}')
        except Exception as e:
            print(f'Other error: {e}')
        return False

    def requires_replan(self, robot_name: str):
        """Return True if the robot needs RMF to replan its route."""
        response = self.data(robot_name)
        if response:
            return response['data'].get('replan', False)
        return False

    def data(self, robot_name=None):
        """Return the full status data of the robot as a dict.
        Return None if any error occurs."""
        # TODO: Replace with your robot's status endpoint
        if robot_name:
            url = self.prefix + f'/status?robot={robot_name}'
        else:
            url = self.prefix + '/status'
        try:
            r = requests.get(url, timeout=self.timeout)
            r.raise_for_status()
            if self.debug:
                print(f'Response: {r.json()}')
            return r.json()
        except HTTPError as e:
            print(f'HTTP error: {e}')
        except Exception as e:
            print(f'Other error: {e}')
        return None
