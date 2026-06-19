# open-rmf-fleet-template

A complete, ready-to-run **ROS2 + Open-RMF** workspace for learning and prototyping autonomous robot fleet management. Includes a minimal custom fleet adapter, office map, patrol tasks, and full Gazebo + RViz simulation — all from scratch.

---

## 📦 Workspace Structure

```
rmf-learning/
└── src/
    ├── rmf_demos/              # Open-RMF official demos (submodule)
    └── rmf_scratch/            # Our custom minimal fleet system
        ├── rmf_scratch/                 # Robot config (speeds, battery, waypoints)
        ├── rmf_scratch_maps/            # Office map (Traffic Editor)
        ├── rmf_scratch_fleet_adapter/   # Custom Fleet Adapter (100% original!)
        ├── rmf_scratch_tasks/           # Task dispatcher (patrol)
        ├── rmf_scratch_gz/              # Gazebo + RViz launcher
        └── rmf_scratch_assets/          # 3D models
```

---

## 🚀 Installation

### 1. Clone the workspace (with submodules)
```bash
git clone --recurse-submodules <this_repo_url> rmf-learning
cd rmf-learning
```

> If you forgot `--recurse-submodules`:
> ```bash
> git submodule update --init --recursive
> ```

### 2. Install ROS2 dependencies
```bash
sudo apt update
rosdep update
rosdep install --from-paths src --ignore-src -r -y
```

### 3. Build
```bash
colcon build
source install/setup.bash
```

---

## 🎮 Running the Simulation

### Launch everything (Gazebo + RViz + RMF)
```bash
source install/setup.bash
ros2 launch rmf_scratch_gz office.launch.xml
```

### Send a patrol task (new terminal)
```bash
source install/setup.bash
ros2 run rmf_scratch_tasks dispatch_patrol -p mining_zone_1 -n 1 --use_sim_time
```

---

## 🗺️ Map Waypoints

| Waypoint | Role |
|---|---|
| `base_station` | Robot spawn point, charger, holding point |
| `mining_zone_1` | Patrol target destination |

---

## 🤖 How It Works

```
You run dispatch_patrol
        ↓
RMF opens a bid (auction)
        ↓
rmf_scratch_fleet_adapter evaluates cost
        ↓
Adapter wins bid → robot gets task
        ↓
tinyRobot1 navigates: base_station → mining_zone_1
        ↓
Robot returns to base_station automatically
```

---

## 🔧 Customization

### Add a new waypoint
1. Open Traffic Editor:
```bash
traffic-editor src/rmf_scratch/rmf_scratch_maps/maps/office/office.building.yaml
```
2. Add waypoint, draw lanes
3. Rebuild: `colcon build --packages-select rmf_scratch_maps`
4. Send task: `ros2 run rmf_scratch_tasks dispatch_patrol -p <new_waypoint> -n 1 --use_sim_time`

### Add a second robot
Edit `src/rmf_scratch/rmf_scratch/config/tinyRobot_config.yaml` — add `tinyRobot2` entry.

---

## 📊 RViz Visualization

After launching, open RViz and add these displays:

| Topic | Display Type | QoS |
|---|---|---|
| `/floorplan` | Map | Durability: **Transient Local** |
| `/fleet_markers` | MarkerArray | Default |
| `/schedule_markers` | MarkerArray | Default |
| `/building_systems_markers` | MarkerArray | Default |

---

## 🌐 Real Robot Integration

To replace the Gazebo simulation with a physical robot:

1. Edit `RobotClientAPI.py` → replace REST calls with your robot's API (HTTP/MQTT)
2. Set `use_sim_time: false`
3. Run your robot's SLAM + Nav2 stack
4. RMF bidding, scheduling, and conflict resolution works unchanged

---

## 📚 References

- [Open-RMF Book](https://osrf.github.io/ros2multirobotbook/)
- [RMF Demos](https://github.com/open-rmf/rmf_demos)
- [Traffic Editor](https://github.com/open-rmf/rmf_traffic_editor)
- [ROS2 Humble Docs](https://docs.ros.org/en/humble/)

---

## 📄 License

Apache License 2.0
