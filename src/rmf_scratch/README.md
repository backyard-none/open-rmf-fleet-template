# RMF Scratch — Minimal ROS2 Fleet Management Template

A clean, minimal, and fully self-contained **Open-RMF** workspace for learning and prototyping robot fleet management systems. Built from scratch without unnecessary demo dependencies.

---

## 🏗️ Package Structure

```
rmf_scratch/
├── rmf_scratch/                  # Robot configuration (speeds, battery, start waypoints)
├── rmf_scratch_maps/             # Office map (Traffic Editor → Gazebo world)
├── rmf_scratch_fleet_adapter/    # Custom Fleet Adapter + Fleet Manager (100% ours!)
├── rmf_scratch_tasks/            # Task dispatcher (patrol)
├── rmf_scratch_gz/               # Simulation launcher + RViz config
└── rmf_scratch_assets/           # 3D models (extendable)
```

---

## 🚀 Quick Start

### Prerequisites
- ROS2 Humble
- Gazebo Ignition (Fortress)
- Open-RMF packages

### 1. Clone dependencies
```bash
mkdir -p ~/rmf_ws/src && cd ~/rmf_ws/src
git clone https://github.com/open-rmf/rmf_demos.git
git clone <this_repo_url> rmf_scratch
```

### 2. Build
```bash
cd ~/rmf_ws
colcon build
source install/setup.bash
```

### 3. Launch simulation
```bash
ros2 launch rmf_scratch_gz office.launch.xml
```

### 4. Send a patrol task (in a new terminal)
```bash
source install/setup.bash
ros2 run rmf_scratch_tasks dispatch_patrol -p mining_zone_1 -n 1 --use_sim_time
```

---

## 📦 Package Details

### `rmf_scratch`
Holds the robot fleet configuration YAML file (`tinyRobot_config.yaml`).
Defines robot name, speed limits, battery profile, and starting waypoint (`base_station`).

### `rmf_scratch_maps`
Contains the office building map (`office.building.yaml`) drawn with **Traffic Editor**.
`colcon build` automatically converts it into:
- A Gazebo `.world` 3D simulation file
- A `nav_graphs/0.yaml` navigation graph for the fleet adapter

**Waypoints:**
| Name | Role |
|---|---|
| `base_station` | Robot spawn, charger, holding point |
| `mining_zone_1` | Patrol target |

### `rmf_scratch_fleet_adapter`
Our own custom fleet adapter — **fully independent from rmf_demos_fleet_adapter**.

Key files:
- `fleet_adapter.py` — Connects RMF task system to the robot API
- `fleet_manager.py` — REST API server that tracks robot state (position, battery)
- `RobotClientAPI.py` — Communication interface between adapter and manager
- `RobotCommandHandle.py` — Handles robot movement commands and state tracking

The fleet adapter natively supports `patrol` task type.

### `rmf_scratch_tasks`
Task dispatcher scripts.

```bash
# Send a patrol task
ros2 run rmf_scratch_tasks dispatch_patrol -p <waypoint_name> -n <rounds> --use_sim_time
```

### `rmf_scratch_gz`
Launch file and RViz configuration for the Gazebo simulation.

```bash
ros2 launch rmf_scratch_gz office.launch.xml
```

Launches:
- Gazebo Ignition (3D simulation)
- RViz2 (fleet visualization)
- RMF Traffic Schedule
- RMF Task Dispatcher
- Fleet Adapter + Fleet Manager
- Building Map Server

---

## 🗺️ Map Customization

1. Open Traffic Editor:
```bash
traffic-editor src/rmf_scratch/rmf_scratch_maps/maps/office/office.building.yaml
```

2. Add/edit waypoints, lanes, doors
3. Rebuild:
```bash
colcon build --packages-select rmf_scratch_maps
```

---

## 🤖 How the Bidding System Works

```
You send a task request
        ↓
RMF Dispatcher opens a bid
        ↓
Fleet Adapter evaluates cost (distance + battery)
        ↓
Submits bid proposal
        ↓
Dispatcher awards task to best robot
        ↓
Robot navigates to target waypoint
        ↓
Robot returns to base_station
```

---

## 🔧 Adding a New Robot

1. Edit `rmf_scratch/config/tinyRobot_config.yaml`:
```yaml
robots:
  tinyRobot1:
    ...
  tinyRobot2:           # Add this
    start:
      waypoint: "base_station"
```

2. Add spawn to `office.building.yaml` (Traffic Editor)
3. Rebuild and relaunch

---

## 🌐 Real Robot Integration

To connect a physical robot instead of the Gazebo simulation:

1. Replace `RobotClientAPI.py` with your robot's HTTP/MQTT API calls
2. Set `use_sim_time: false` in the launch file
3. Run your robot's navigation stack (Nav2 + SLAM)
4. The rest of RMF (bidding, scheduling, conflict resolution) stays the same!

```
RMF Fleet Adapter → MQTT Bridge → Raspberry Pi → Real Robot
```

---

## 📋 RViz Visualization Topics

| Topic | Type | Shows |
|---|---|---|
| `/floorplan` | Map | 2D office floor plan |
| `/fleet_markers` | MarkerArray | Robot positions |
| `/schedule_markers` | MarkerArray | Planned routes |
| `/building_systems_markers` | MarkerArray | Doors and lifts |

> **Tip:** Set `/floorplan` QoS Durability to `Transient Local` in RViz for the map to appear.

---

## 📚 References

- [Open-RMF Documentation](https://osrf.github.io/ros2multirobotbook/)
- [RMF Demos Repository](https://github.com/open-rmf/rmf_demos)
- [Traffic Editor](https://github.com/open-rmf/rmf_traffic_editor)
- [ROS2 Humble](https://docs.ros.org/en/humble/)

---

## 📄 License

Apache License 2.0
