# PPC-Dataset-ROS2

Unofficial ROS 2 conversion of the [PPC-Dataset](https://github.com/taroz/PPC-Dataset)
by Taro Suzuki. Please cite the original dataset when using these recordings.

The bags use the message definitions of
[gnss_ros_standardization](https://github.com/DaikiNiimi/gnss_ros_standardization).
Build the release of that package that matches this dataset; the message
definitions must be identical for the bags to deserialize.

## Contents and time convention

| Topic | ROS type | Nominal rate | Source |
|---|---|---|---|
| `/gnss/observation` | `gnss_ros_standardization/msg/GnssObservations` | 5 Hz | `rover.obs` |
| `/base/gnss/observation` | `gnss_ros_standardization/msg/GnssObservations` | 1 Hz | `base.obs` |
| `/gnss/ephemeris` | `gnss_ros_standardization/msg/GnssEphemerides` | at transmission time | `base.nav` |
| `/gnss/imu/data_raw` | `sensor_msgs/msg/Imu` | 100 Hz | `imu.csv` |
| `/gnss/reference/solution` | `gnss_ros_standardization/msg/GnssSolution` | 5 Hz | `reference.csv` |
| `/gnss/reference/solution_odom` | `nav_msgs/msg/Odometry` | 5 Hz | `reference.csv` |

Header stamps and bag timestamps use **GPST, not UTC**. GNSS week/TOW is also
GPST. Each bag includes `gnss_time_basis.yaml`; do not interpret the timestamps
as UTC without a time-scale conversion. Source gaps are kept; missing epochs are
not interpolated.

IMU acceleration is in m/s², angular velocity in rad/s (converted from deg/s),
in the source axes (`imu_link`), without lever-arm correction. The reference
solution keeps the source LLH/ECEF position and ENU velocity; its `pos_enu` is
relative to the first reference position, recorded in `pos_enu_org_ecef`.
Values the source does not provide (`age_diff`, DOP and covariances) are NaN. The
reference Odometry uses the same origin as the ENU `map` frame; attitude is in
`map` (from roll, pitch and heading clockwise from North), linear twist in
`base_link`.

## Runs

| Run | First observation (GPST) | Duration | Messages | MCAP bytes |
|---|---|---|---|---|
| `nagoya_run1` | 2024-08-03 08:53:00 | 1530 s | 177,457 | 27,266,898 |
| `nagoya_run2` | 2024-07-20 10:22:00 | 1890 s | 219,263 | 33,834,240 |
| `nagoya_run3` | 2024-08-03 09:50:00 | 1040 s | 120,656 | 18,247,638 |
| `tokyo_run1` | 2024-07-23 04:04:30 | 2390 s | 277,244 | 39,065,495 |
| `tokyo_run2` | 2024-07-23 01:10:00 | 1830 s | 212,447 | 35,394,262 |
| `tokyo_run3` | 2024-07-23 01:51:00 | 3060 s | 355,244 | 59,684,988 |

`bags/<run>/` contains one MCAP file (lossless Zstandard chunk compression), the
metadata and the time-basis sidecar. Each MCAP file is below 100 MB.

## Navigation messages

Each navigation record is published at its transmission time (RINEX `ttr`;
GLONASS `tof`), as a receiver stream delivers it in real time. Records
transmitted before the first observation epoch are published together **1 s
before the first observation**, so that playback delivers them before the first
epoch. Records transmitted after the last observation epoch are omitted.

Each message also carries the ionosphere parameters of the `base.nav` header
(GPS, Galileo, QZSS, BeiDou). The topics carry legacy Kepler GPS/Galileo/QZSS/BeiDou
ephemerides and GLONASS ephemerides: **8,256 records** across the six runs. The source files contain
20,712 records (a file shared by several runs is counted once for each run). Not
published are the 5,698 SBAS records, which the message types cannot represent;
records without an orbit, which receivers publish as "unhealthy, no orbit"; and
records transmitted after the last epoch.

## What was checked

- Observations: all 12 RINEX observation files were parsed independently of
  RTKLIB's `obs_t` selection. **70,380 epochs and 8,345,592 signal
  observations** matched the topics: satellite/signal identity, week/TOW,
  P/L/D/CN0, missing components, LLI bits and GLONASS frequency channels.
  BeiDou C51–C63 are kept. P and L use absolute tolerance 1e-6; float32 D/CN0
  use `max(1e-6, abs(source) * 6e-8)`. Identifiers, flags and counts match
  exactly.
- A zero measurement value in these bags comes from a zero (missing) field in the
  source RINEX files; treat it as missing.
- Navigation: every published record matched the fields of its source record.
- IMU and reference: every CSV row matched its message (header time within 1 µs).
- Playback: each compressed bag was played into a new recorder; all topic
  counts and ordered payload hashes matched.

## Replay

```bash
source /opt/ros/jazzy/setup.bash
source /path/to/gnss_ros_standardization/install/setup.bash
ros2 bag info bags/nagoya_run1
ros2 bag play bags/nagoya_run1 --rate 1
```

Use reliable subscriptions; the navigation topic uses transient-local
durability. Start subscribers before playback if every message must be received.
The player offers the recorded history depth: 2000 for the observation and
reference topics, 20000 for the IMU and 256 for the navigation topic.

## Reproduce

Each run was converted with the software's `rinex_to_rosbag` (default
`--eph-mode transmission`):

```bash
ros2 run gnss_ros_standardization rinex_to_rosbag \
  --obs rover=/path/to/run/rover.obs --obs base=/path/to/run/base.obs \
  --nav /path/to/run/base.nav \
  --topic-obs rover=/gnss/observation --topic-obs base=/base/gnss/observation \
  --timestamp-scale gpst --storage mcap --out /path/to/new-bag \
  --imu /path/to/run/imu.csv --imu-frame raw --reference /path/to/run/reference.csv
```

It was then compressed with `ros2 bag convert` and this configuration:

```yaml
output_bags:
  - uri: /path/to/compressed-bag
    storage_id: mcap
    storage_preset_profile: zstd_small
    all_topics: true
```

```bash
ros2 bag convert -i /path/to/new-bag mcap -o compression.yaml
cp /path/to/new-bag/gnss_time_basis.yaml /path/to/compressed-bag/
```

Compressed bytes can vary with library versions. To compare a regenerated bag,
compare the decoded payloads and timestamps, not the file hash. To produce
sqlite3 instead, use `storage_id: sqlite3` and omit `storage_preset_profile`.

## License

MIT. See [LICENSE](LICENSE). Derived from PPC-Dataset, Copyright (c) 2025 Taro
Suzuki. No upstream endorsement is implied.
