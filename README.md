# PPC-Dataset-ROS2

Unofficial ROS 2 bag conversion of the [PPC-Dataset](https://github.com/taroz/PPC-Dataset)
using the message definitions from
[gnss_ros_standardization](https://github.com/DaikiNiimi/gnss_ros_standardization).

The **PPC-Dataset** (Precise Positioning Challenge Dataset, by Taro Suzuki, MIT License) is
six urban driving runs — three in Nagoya, three in Tokyo — with 5 Hz triple-frequency
multi-GNSS observations, 100 Hz IMU, reference-station observations, and ground truth.
For anything about the data itself (receivers, antennas, routes, ground-truth generation),
refer to the original repository. **If you use this data, please cite the original dataset.**

## gnss_ros_standardization

[**gnss_ros_standardization**](https://github.com/DaikiNiimi/gnss_ros_standardization)
defines standardized ROS 2 message types for raw GNSS data — observations, ephemerides,
and positioning solutions — so that GNSS datasets and receivers can be replayed into ROS 2
positioning pipelines (RTK, factor-graph optimization, EKF) through a common interface.

Its converters are **bidirectional**: RINEX ↔ rosbag and RTKLIB `.pos` ↔ rosbag. These bags
were produced with `rinex_to_rosbag`, and the same package converts a bag back out — a
solution computed in ROS 2 can be handed to RTKLIB or any conventional GNSS tooling, and
your own RINEX logs can join this dataset on the same topics.

Build the package (see its README) before `ros2 bag play`, so the GNSS message types resolve.

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

- Timestamps are **GPS time (GPST)**, not UTC. Use the `week` / `tow` fields inside the GNSS
  messages for canonical GNSS time.

## Runs

| Run | Start (GPST) | Duration | Messages | Size |
|---|---|---|---|---|
| `nagoya_run1` | 2024-08-03 08:53:00 | 1530 s | 177,454 | 26.7 MB |
| `nagoya_run2` | 2024-07-20 10:22:00 | 1890 s | 219,260 | 33.2 MB |
| `nagoya_run3` | 2024-08-03 09:50:00 | 1040 s | 120,654 | 17.9 MB |
| `tokyo_run1` | 2024-07-23 04:04:30 | 2390 s | 277,245 | 38.1 MB |
| `tokyo_run2` | 2024-07-23 01:10:00 | 1830 s | 212,300 | 34.6 MB |
| `tokyo_run3` | 2024-07-23 01:51:00 | 3060 s | 354,984 | 58.2 MB |

Each run is `bags/<run>/<run>_0.mcap` plus `metadata.yaml`.

## Converting to sqlite3 (.db3)

The bags ship as mcap, the rosbag2 default since Iron. For sqlite3, write `to_sqlite3.yaml`:

```yaml
output_bags:
  - uri: nagoya_run1_db3
    storage_id: sqlite3
    all_topics: true
```

```bash
ros2 bag convert -i bags/nagoya_run1 mcap -o to_sqlite3.yaml
```

Note that sqlite3 bags are not compressed (`nagoya_run3`: 18 MB → 94 MB). On Humble or
earlier, if mcap is not recognized: `sudo apt install ros-$ROS_DISTRO-rosbag2-storage-mcap`.

## License

MIT. See [LICENSE](LICENSE). The bags are derived from the PPC-Dataset
(Copyright (c) 2025 Taro Suzuki, MIT License).
