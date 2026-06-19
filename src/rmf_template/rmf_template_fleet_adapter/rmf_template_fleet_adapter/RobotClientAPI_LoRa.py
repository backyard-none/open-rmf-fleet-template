# Robot Fleet - RobotClientAPI (LoRa Version)
# Uses serial communication to a LoRa gateway module.
# Replace RobotClientAPI.py with this file for LoRa-based robots.
#
# Expected LoRa packet format (plain text, comma-separated):
#   Robot → Gateway:  "POS,<robot>,<x>,<y>,<yaw>,<battery>,<last_cmd>"
#   Gateway → Robot:  "NAV,<robot>,<x>,<y>,<yaw>,<speed>"
#                     "STP,<robot>,<cmd_id>"
#                     "TSK,<robot>,<cmd_id>,<task>"

import serial
import threading
import time
from typing import Dict, Optional


# -----------------------------------------------------------------------
# Packet builder helpers
# -----------------------------------------------------------------------

def _build_nav_packet(robot_name: str, cmd_id: int,
                      x: float, y: float, yaw: float,
                      speed_limit: float) -> bytes:
    msg = f"NAV,{robot_name},{cmd_id},{x:.3f},{y:.3f},{yaw:.4f},{speed_limit:.2f}\n"
    return msg.encode()


def _build_stop_packet(robot_name: str, cmd_id: int) -> bytes:
    msg = f"STP,{robot_name},{cmd_id}\n"
    return msg.encode()


def _build_task_packet(robot_name: str, cmd_id: int,
                       task: str, map_name: str) -> bytes:
    msg = f"TSK,{robot_name},{cmd_id},{task},{map_name}\n"
    return msg.encode()


# -----------------------------------------------------------------------
# RobotAPI - LoRa Serial Implementation
# -----------------------------------------------------------------------

class RobotAPI:
    def __init__(self,
                 port: str = '/dev/ttyUSB0',
                 baudrate: int = 9600,
                 timeout: float = 5.0):
        """
        Connect to the LoRa gateway via serial port.

        Args:
            port:     Serial port of the LoRa gateway (e.g. /dev/ttyUSB0)
            baudrate: Baud rate matching the LoRa module (default 9600)
            timeout:  Read timeout in seconds
        """
        # TODO: Set port and baudrate to match your LoRa gateway
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.debug = False

        # Latest state received from each robot
        # Format: { robot_name: { x, y, yaw, battery, last_cmd } }
        self._robot_states: Dict[str, dict] = {}
        self._lock = threading.Lock()

        # Open serial connection to LoRa gateway
        try:
            self._serial = serial.Serial(port, baudrate, timeout=timeout)
            print(f'[LoRa] Connected to gateway on {port} @ {baudrate} baud')
        except Exception as e:
            print(f'[LoRa] Failed to open serial port {port}: {e}')
            self._serial = None

        # Background thread to continuously read incoming LoRa packets
        self._reader_thread = threading.Thread(
            target=self._read_loop, daemon=True)
        self._reader_thread.start()

    # -------------------------------------------------------------------
    # Background reader — parses incoming packets from robots
    # -------------------------------------------------------------------

    def _read_loop(self):
        """Continuously read packets from the LoRa gateway serial port."""
        while True:
            if self._serial is None or not self._serial.is_open:
                time.sleep(1.0)
                continue
            try:
                line = self._serial.readline().decode('utf-8').strip()
                if line:
                    self._parse_packet(line)
            except Exception as e:
                print(f'[LoRa] Read error: {e}')
                time.sleep(0.5)

    def _parse_packet(self, line: str):
        """
        Parse a status packet from a robot.
        Expected format: POS,<robot>,<x>,<y>,<yaw>,<battery>,<last_cmd>
        TODO: Adjust to match your robot's actual packet format.
        """
        if self.debug:
            print(f'[LoRa] Received: {line}')

        parts = line.split(',')
        if len(parts) < 7 or parts[0] != 'POS':
            return

        try:
            robot_name = parts[1]
            state = {
                'x':        float(parts[2]),
                'y':        float(parts[3]),
                'yaw':      float(parts[4]),
                'battery':  float(parts[5]),   # 0.0 – 100.0
                'last_cmd': int(parts[6])
            }
            with self._lock:
                self._robot_states[robot_name] = state

            if self.debug:
                print(f'[LoRa] State updated for {robot_name}: {state}')

        except (ValueError, IndexError) as e:
            print(f'[LoRa] Failed to parse packet "{line}": {e}')

    # -------------------------------------------------------------------
    # Internal send helper
    # -------------------------------------------------------------------

    def _send(self, packet: bytes) -> bool:
        """Send a packet over serial to the LoRa gateway."""
        if self._serial is None or not self._serial.is_open:
            print('[LoRa] Serial port not open')
            return False
        try:
            self._serial.write(packet)
            if self.debug:
                print(f'[LoRa] Sent: {packet}')
            return True
        except Exception as e:
            print(f'[LoRa] Send error: {e}')
            return False

    # -------------------------------------------------------------------
    # Public API — called by RobotCommandHandle
    # -------------------------------------------------------------------

    def position(self, robot_name: str) -> Optional[list]:
        """Return [x, y, theta] in metres and radians, or None."""
        with self._lock:
            state = self._robot_states.get(robot_name)
        if state is None:
            return None
        return [state['x'], state['y'], state['yaw']]

    def navigate(self, robot_name: str, cmd_id: int,
                 pose, map_name: str, speed_limit: float = 0.0) -> bool:
        """
        Send a navigation command to the robot via LoRa.
        Return True if the packet was sent successfully.
        """
        assert len(pose) >= 3
        packet = _build_nav_packet(
            robot_name, cmd_id, pose[0], pose[1], pose[2], speed_limit)
        return self._send(packet)

    def stop(self, robot_name: str, cmd_id: int) -> bool:
        """Send a stop command to the robot. Return True if sent."""
        packet = _build_stop_packet(robot_name, cmd_id)
        return self._send(packet)

    def start_process(self, robot_name: str, cmd_id: int,
                      process: str, map_name: str) -> bool:
        """
        Send a custom task command (e.g. mine, load, unload).
        Return True if sent successfully.
        TODO: Expand task types to match your robot's capabilities.
        """
        packet = _build_task_packet(robot_name, cmd_id, process, map_name)
        return self._send(packet)

    def navigation_completed(self, robot_name: str, cmd_id: int) -> bool:
        """Return True if the robot reports cmd_id as its last completed command."""
        with self._lock:
            state = self._robot_states.get(robot_name)
        if state is None:
            return False
        return state['last_cmd'] == cmd_id

    def navigation_remaining_duration(self,
                                      robot_name: str,
                                      cmd_id: int) -> Optional[float]:
        """
        Return estimated seconds remaining to reach destination.
        LoRa robots typically do not report this — return None.
        TODO: Implement if your robot firmware supports it.
        """
        return None

    def process_completed(self, robot_name: str, cmd_id: int) -> bool:
        """Return True if the robot's last process matches cmd_id."""
        return self.navigation_completed(robot_name, cmd_id)

    def battery_soc(self, robot_name: str) -> Optional[float]:
        """Return battery state of charge as 0.0–1.0, or None."""
        with self._lock:
            state = self._robot_states.get(robot_name)
        if state is None:
            return None
        return state['battery'] / 100.0

    def requires_replan(self, robot_name: str) -> bool:
        """Return True if the robot needs RMF to replan its route."""
        # TODO: Add 'replan' field to robot packets if needed
        return False

    def check_connection(self) -> bool:
        """Return True if the serial port is open."""
        return self._serial is not None and self._serial.is_open

    def data(self, robot_name: str = None) -> Optional[dict]:
        """
        Return full robot state as a dict compatible with fleet_adapter.py.
        This wraps the LoRa state into the same format as the HTTP API.
        """
        with self._lock:
            if robot_name:
                state = self._robot_states.get(robot_name)
                if state is None:
                    return None
                return {
                    'success': True,
                    'data': {
                        'position': {
                            'x':   state['x'],
                            'y':   state['y'],
                            'yaw': state['yaw']
                        },
                        'battery': state['battery'],
                        'last_completed_request': state['last_cmd'],
                        'destination_arrival': None
                    }
                }
            else:
                # Return all robots
                return {
                    name: {
                        'success': True,
                        'data': {
                            'position': {
                                'x': s['x'], 'y': s['y'], 'yaw': s['yaw']
                            },
                            'battery': s['battery'],
                            'last_completed_request': s['last_cmd']
                        }
                    }
                    for name, s in self._robot_states.items()
                }
