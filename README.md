# PPC-Dataset-ROS2

Unofficial ROS 2 conversion of the [PPC-Dataset](https://github.com/taroz/PPC-Dataset)
by Taro Suzuki. Please cite the original dataset when using these recordings.
Build [gnss_ros_standardization](https://github.com/DaikiNiimi/gnss_ros_standardization)
with the message definitions identified in [provenance.json](provenance.json).

These six runs were regenerated from the original RINEX and CSV files and checked
over their entire recorded intervals. The acceptance scope is **lossless GNSS
observation fields within the output types' precision, selected supported navigation
records with the original navigation files included**. This is not a claim that
every source navigation record is available as a ROS message.

## Contents and time convention

| Topic | ROS type | Nominal rate | Source |
|---|---|---|---|
| `/gnss/observation` | `gnss_ros_standardization/msg/GnssObservations` | 5 Hz | `rover.obs` |
| `/base/gnss/observation` | `gnss_ros_standardization/msg/GnssObservations` | 1 Hz | `base.obs` |
| `/gnss/ephemeris` | `gnss_ros_standardization/msg/GnssEphemerides` | on change | selected `base.nav` records |
| `/gnss/imu/data_raw` | `sensor_msgs/msg/Imu` | 100 Hz | `imu.csv` |
| `/gnss/reference/solution` | `gnss_ros_standardization/msg/GnssSolution` | 5 Hz | `reference.csv` |
| `/gnss/reference/solution_odom` | `nav_msgs/msg/Odometry` | 5 Hz | `reference.csv` |

Headers and original bag timestamps use **GPST, not UTC**, preserving the previous
dataset convention. GNSS week/TOW is also GPST. Each bag includes
`gnss_time_basis.yaml`; timestamps must not be interpreted as UTC without a time-scale
conversion. Source gaps are retained; missing epochs are not interpolated.

IMU acceleration is in m/s²; angular velocity is converted from degrees/s to rad/s.
The raw source axes are retained, labelled `imu_link`, with no lever-arm correction.
Reference solution retains the source LLH/ECEF position and ENU velocity. Reference
Odometry uses the first reference position as the fixed ENU `map` origin, expresses
attitude in that map, and expresses linear twist in `base_link`. The CSV attitude
conversion uses roll/pitch and heading clockwise from North. The older conversion's
zero Odometry positions and ENU velocity labelled as body velocity are corrected.
This verifies the stated field conversion, not physical mounting/calibration accuracy.
Tokyo lever-arm descriptions differ in the upstream documentation; no positioning
accuracy certification is made here.

## Runs

| Run | Start (GPST) | Duration | Messages | MCAP bytes |
|---|---|---|---|---|
| `nagoya_run1` | 2024-08-03 08:53:00 | 1530 s | 177,454 | 27,282,735 |
| `nagoya_run2` | 2024-07-20 10:22:00 | 1890 s | 219,260 | 33,863,952 |
| `nagoya_run3` | 2024-08-03 09:50:00 | 1040 s | 120,654 | 18,226,140 |
| `tokyo_run1` | 2024-07-23 04:04:30 | 2390 s | 277,245 | 39,137,936 |
| `tokyo_run2` | 2024-07-23 01:10:00 | 1830 s | 212,300 | 35,455,278 |
| `tokyo_run3` | 2024-07-23 01:51:00 | 3060 s | 354,984 | 59,757,728 |

`bags/<run>/` contains MCAP with lossless Zstandard chunk compression, metadata and
the time-basis sidecar. Each MCAP file is below 100 MB.

## What was checked

All 12 observation files were parsed independently of RTKLIB's `obs_t` selection:
**70,380 epochs and 8,345,592 signal observations** matched the resulting topics.
Checks cover satellite/signal identity, week/TOW, P/L/D/CN0, missing components,
source LLI bits and GLONASS frequency-channel encoding. BeiDou C51–C63 is retained.
P and L use absolute tolerance 1e-6; float32 D/CN0 use
`max(1e-6, abs(source) * 6e-8)`. Identifiers, flags and counts must match exactly.
RINEX blank/zero measurement fields denote missing data under RINEX 3.04.
The current RINEX converter retains those backend zero sentinels; zero in these
bags must not automatically be treated as a measured value. Explicit invalid
receiver components on other input paths may instead use NaN; see the software's
`OBSERVATIONS.md` for the input-specific contract.
The lossless claim concerns these observation fields: RINEX SSI, textual headers
and receiver metadata are not fields of `GnssObservation`. Header information and
source file hashes are retained in the validation reports.

All IMU/reference CSV rows and all selected navigation records were compared with
the originals. Header/bag time tolerance is 1 microsecond for numerical conversion;
navigation snapshot headers match the corresponding observation epoch.
The compressed bags preserve original storage timestamps and message payloads.
Each compressed run was actually played at 50× speed into a subscriber and a new
rosbag recorder. All topic counts and ordered payload hashes matched. Up to three
trailing CDR alignment bytes are normalized; no message field is omitted.
Re-recorded bag storage timestamps represent the new reception time; message header
timestamps remain unchanged. QoS and per-topic counts are in the metadata/provenance.

See [validation/](validation/) for per-run differences/counts and
[provenance.json](provenance.json) for source hashes, schema hashes, software revision
plus the uncommitted source manifest, ROS/storage versions and output hashes.
These RINEX/CSV checks do not certify receiver binary formats or physical timing.

## Navigation scope and original files

The converter emits on-change snapshots selected for satellites at observation
epochs, using its documented validity windows. Topics contain legacy Kepler
GPS/Galileo/QZSS/BeiDou ephemerides and GLONASS ephemerides, **664 selected records**
across the six runs. This is not an archive of all navigation records in the source.

The six input files contain **20,712 records**, including **5,698 SBAS records** that
the fixed ROS messages cannot represent. These counts include the repeated input
files shared by multiple runs. Other records are not selected because of observation
times, satellites, validity windows or snapshot selection. Per-run selected and
unselected counts are in `validation/*-navigation.json`.

Byte-identical originals are provided in `source_navigation/<run>/base.nav`, with
the upstream license in `source_navigation/LICENSE`. Use those files for complete
navigation retention or for a different selection policy. Including them does not
make the navigation topic lossless.

## Replay

```bash
source /opt/ros/jazzy/setup.bash
source /path/to/gnss_ros_standardization/install-core/setup.bash
ros2 bag info bags/nagoya_run1
ros2 bag play bags/nagoya_run1 --rate 1
```

Use reliable subscriptions; the navigation topic offers transient-local durability.
Start subscribers before playback when complete recording is required. Temporal
filters/estimators must reset or restart when looping or seeking backwards; these
messages do not provide a session-reset event. These files use the current six
schemas. No old-bag migration adapter is provided.

## Reproduce

In the software repository, with the same source manifest and dependencies:

```bash
source /opt/ros/jazzy/setup.bash
source install-core/setup.bash
export ROS_LOG_DIR="$PWD/log/ppc-reproduction/ros"
PPC_SOURCE=/path/to/PPC-Dataset
PPC_OUTPUT="$PWD/log/ppc-reproduction/candidates"
python3 test/audit_ppc_observations.py --dataset "$PPC_SOURCE" \
  --converter "$PWD/install-core/gnss_ros_standardization/lib/gnss_ros_standardization/rinex_to_rosbag" \
  --output "$PPC_OUTPUT" --full-topics
for city in nagoya tokyo; do
  for run in run1 run2 run3; do
    name="${city}_${run}"
    python3 test/audit_ppc_navigation.py --source "$PPC_SOURCE/$city/$run/base.nav" \
      --bag "$PPC_OUTPUT/$name-candidate" --report "$PPC_OUTPUT/$name-navigation.json"
    python3 test/audit_ppc_csv.py --source "$PPC_SOURCE/$city/$run" \
      --bag "$PPC_OUTPUT/$name-candidate" --report "$PPC_OUTPUT/$name-csv.json"
  done
done
python3 test/check_ppc_playback.py --candidates "$PPC_OUTPUT" \
  --output "$PWD/log/ppc-reproduction/playback" --rate 50
```

The conversion invoked for each run is:

```bash
ros2 run gnss_ros_standardization rinex_to_rosbag \
  --obs rover=/path/to/run/rover.obs --obs base=/path/to/run/base.obs \
  --nav /path/to/run/base.nav \
  --topic-obs rover=/gnss/observation --topic-obs base=/base/gnss/observation \
  --timestamp-scale gpst --storage mcap --out /path/to/new-bag \
  --imu /path/to/run/imu.csv --imu-frame raw --reference /path/to/run/reference.csv
```

For each run, compress to a new directory using `ros2 bag convert` and this configuration:

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

Run the playback checker again on the compressed directories before publication.
Compression bytes can vary with library versions; validate decoded payloads and
timestamps, not just a regenerated compressed file's hash. To produce sqlite3 instead,
use `storage_id: sqlite3` and omit `storage_preset_profile`.

## License

MIT. See [LICENSE](LICENSE) and [upstream license](source_navigation/LICENSE).
Derived from PPC-Dataset, Copyright (c) 2025 Taro Suzuki. No upstream endorsement is implied.
