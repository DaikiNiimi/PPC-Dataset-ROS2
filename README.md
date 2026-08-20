# PPC-Dataset-ROS2

ROS 2 rosbag2 conversion of the **Precise Positioning Challenge (PPC) Dataset** — six urban
driving runs (three in Nagoya, three in Tokyo) with 5 Hz triple-frequency multi-GNSS
observations, 100 Hz IMU, reference-station observations, and ground truth, packaged as
ready-to-play ROS 2 bags.

The bags are included in this repository. No separate download is required:

```bash
git clone https://github.com/DaikiNiimi/PPC-Dataset-ROS2.git
ros2 bag play PPC-Dataset-ROS2/bags/nagoya_run1
```

Total size is 209 MB across six runs (mcap with zstd chunk compression). Git LFS is not used.

## Original dataset

The source data is the [PPC-Dataset](https://github.com/taroz/PPC-Dataset) by Taro Suzuki,
released under the MIT License. It provides RINEX observations, IMU CSV, ground truth, and
KML trajectories for vehicles driven in urban Nagoya and Tokyo.

**For anything about the data itself** — receivers and antennas, reference-station
coordinates, driving routes, ground-truth generation, and the observation environment —
please refer to the original repository. This repository does not restate it; it documents
only what is specific to the ROS 2 packaging.

If you use this data, please cite the original dataset.

## How it was converted

The bags were produced with
[gnss_ros_standardization](https://github.com/DaikiNiimi/gnss_ros_standardization), which
defines standardized ROS 2 message types for raw GNSS data and ships a `rinex_to_rosbag`
converter. The original RINEX observations, broadcast ephemerides, IMU CSV, and ground truth
are mapped onto ROS 2 topics so that the dataset can be replayed directly into ROS 2
positioning pipelines (RTK, factor-graph optimization, EKF) without any format handling of
your own.

Observations, IMU samples, and ground truth are converted verbatim — no filtering,
smoothing, or resampling. Ephemerides are the one exception: rather than dumping `base.nav`
record by record, the converter publishes the ephemeris selected for each epoch, mirroring
RTKLIB's `seleph()`, so that a node consuming the bag makes the same per-satellite choice
that `rnx2rtkp` makes reading the RINEX directly. This is why `/gnss/ephemeris` carries only
a few dozen messages per run.

## Directory structure

```
PPC-Dataset-ROS2
│   README.md : This file
│   LICENSE   : MIT (this repository) + MIT (original PPC-Dataset)
│
└───bags
    └───nagoya_run1
    │   │   nagoya_run1_0.mcap : Messages (mcap, zstd chunk compression)
    │   │   metadata.yaml      : rosbag2 metadata (topics, QoS, counts)
    └───nagoya_run2
    │   │   ...
    └───nagoya_run3
    │   │   ...
    └───tokyo_run1
    │   │   ...
    └───tokyo_run2
    │   │   ...
    └───tokyo_run3
        │   ...
```

## Converting to sqlite3 (.db3)

The bags ship as mcap, the default rosbag2 storage format since ROS 2 Iron. If you need
sqlite3, convert locally with `ros2 bag convert`. Write this to `to_sqlite3.yaml`:

```yaml
output_bags:
  - uri: nagoya_run1_db3
    storage_id: sqlite3
    all_topics: true
```

Then:

```bash
ros2 bag convert -i bags/nagoya_run1 mcap -o to_sqlite3.yaml
```

The message definitions are carried into the db3 `message_definitions` table, so the result
is self-describing as well. Note that sqlite3 bags are **not compressed**: `nagoya_run3`
expands from 18 MB to 94 MB.

On Humble or earlier, if mcap is not recognized, install the storage plugin instead:

```bash
sudo apt install ros-$ROS_DISTRO-rosbag2-storage-mcap
```

## ROS 2 topics

Every run contains the same six topics.

| Topic | Type | Rate | Source |
|---|---|---|---|
| `/gnss/observation` | `gnss_ros_standardization/msg/GnssObservations` | 5 Hz | `rover.obs` |
| `/base/gnss/observation` | `gnss_ros_standardization/msg/GnssObservations` | 1 Hz | `base.obs` |
| `/gnss/ephemeris` | `gnss_ros_standardization/msg/GnssEphemerides` | on update | `base.nav` |
| `/gnss/imu/data_raw` | `sensor_msgs/msg/Imu` | 100 Hz | `imu.csv` |
| `/gnss/reference/solution` | `gnss_ros_standardization/msg/GnssSolution` | 5 Hz | `reference.csv` |
| `/gnss/reference/solution_odom` | `nav_msgs/msg/Odometry` | 5 Hz | `reference.csv` |

`/gnss/reference/*` is the ground truth, not a real-time solution. Do not feed it into a
pipeline you intend to evaluate.

### Timestamps

Bag timestamps and message header stamps are **GPS time (GPST)**, not UTC — `rinex_to_rosbag`
has no PC clock to reference, so it derives ROS time from the observation epoch. GPST ran
18 s ahead of UTC during this collection period. For canonical GNSS time, use the `week` and
`tow` fields carried inside the GNSS messages rather than the header stamp.

### Runs

| Run | Start (GPST) | Duration | Messages | Size |
|---|---|---|---|---|
| `nagoya_run1` | 2024-08-03 08:53:00 | 1530 s | 177,454 | 26.7 MB |
| `nagoya_run2` | 2024-07-20 10:22:00 | 1890 s | 219,260 | 33.2 MB |
| `nagoya_run3` | 2024-08-03 09:50:00 | 1040 s | 120,654 | 17.9 MB |
| `tokyo_run1` | 2024-07-23 04:04:30 | 2390 s | 277,245 | 38.1 MB |
| `tokyo_run2` | 2024-07-23 01:10:00 | 1830 s | 212,300 | 34.6 MB |
| `tokyo_run3` | 2024-07-23 01:51:00 | 3060 s | 354,984 | 58.2 MB |

### Reading the custom message types

Three of the six topics use message types defined by `gnss_ros_standardization`. The mcap
files **embed the full message definitions**, so tools that read schemas from the file —
Foxglove, the `mcap` CLI, Python `mcap-ros2-support` — can decode every topic with nothing
installed:

```bash
mcap info bags/nagoya_run1/nagoya_run1_0.mcap
```

To *publish* these topics with `ros2 bag play`, ROS 2 needs the generated typesupport
libraries, so build the package first:

```bash
cd ~/ros2_ws/src && git clone https://github.com/DaikiNiimi/gnss_ros_standardization.git
cd ~/ros2_ws && colcon build --packages-select gnss_ros_standardization
source install/setup.bash
```

## License

MIT. See [LICENSE](LICENSE). The bags are derived from the PPC-Dataset
(Copyright (c) 2025 Taro Suzuki, MIT License).
