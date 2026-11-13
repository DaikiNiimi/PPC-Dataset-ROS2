#!/usr/bin/env python3
"""Score RTKLIB .pos solutions against the reference solution of the bags.

    python3 tools/evaluate.py [--bags bags] [--results results] [--methods rtk,rnx2rtkp,gnss_fgo,gnss_imu_fgo]

Solutions are read from <results>/<run>_<method>.pos (latitude/longitude/height,
GPST), the reference from /gnss/reference/solution of <bags>/<run>. An epoch is
a reference epoch; a solution belongs to it when its time tag is within 2 ms.

    Fix rate       FIX epochs (Q=1) / reference epochs
    Miss Fix rate  FIX epochs with 3D error >= 0.5 m / FIX epochs
    3D <= 0.5 m    epochs with 3D error <= 0.5 m, any Q / reference epochs
    3D RMS         over the epochs that have a solution

Totals are computed from summed epoch counts, not from averaged percentages.
"""
import argparse
import calendar
import math
import os
import sys

import rosbag2_py
from rclpy.serialization import deserialize_message
from gnss_ros_standardization.msg import GnssSolution

RUNS = ['tokyo_run1', 'tokyo_run2', 'tokyo_run3', 'nagoya_run1', 'nagoya_run2', 'nagoya_run3']
GPS_EPOCH = calendar.timegm((1980, 1, 6, 0, 0, 0))
A, F = 6378137.0, 1.0 / 298.257223563  # WGS 84


def llh_to_ecef(lat_deg, lon_deg, h):
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    e2 = F * (2.0 - F)
    n = A / math.sqrt(1.0 - e2 * math.sin(lat) ** 2)
    return ((n + h) * math.cos(lat) * math.cos(lon),
            (n + h) * math.cos(lat) * math.sin(lon),
            (n * (1.0 - e2) + h) * math.sin(lat))


def read_reference(bag):
    """[(time key in ms of GPS time, ECEF position)] in bag order."""
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=bag, storage_id=''), rosbag2_py.ConverterOptions('', ''))
    reader.set_filter(rosbag2_py.StorageFilter(topics=['/gnss/reference/solution']))
    out = []
    while reader.has_next():
        _, data, _ = reader.read_next()
        m = deserialize_message(data, GnssSolution)
        out.append((round((m.time_week * 604800 + m.time_tow) * 1000), (m.pos_ecef.x, m.pos_ecef.y, m.pos_ecef.z)))
    return out


def read_pos(path, epochs):
    """{time key of the reference epoch: (Q, ECEF position)}; the first solution of an epoch is used."""
    out = {}
    with open(path) as f:
        for line in f:
            if line.startswith('%') or not line.strip():
                continue
            c = line.split()
            y, mo, d = (int(v) for v in c[0].split('/'))
            h, mi, s = c[1].split(':')
            t = calendar.timegm((y, mo, d, int(h), int(mi), 0)) - GPS_EPOCH + float(s)
            lat, lon, hgt = float(c[2]), float(c[3]), float(c[4])
            if not all(math.isfinite(v) for v in (lat, lon, hgt)):
                continue
            key = next((k for k in (round(t * 1000) + d for d in (0, -1, 1, -2, 2)) if k in epochs), None)
            if key is not None:
                out.setdefault(key, (int(c[5]), llh_to_ecef(lat, lon, hgt)))
    return out


def count(reference, solution):
    c = dict(epochs=len(reference), solved=0, fix=0, miss=0, within=0, sum_e2=0.0)
    for key, truth in reference:
        if key not in solution:
            continue
        q, p = solution[key]
        e = math.dist(p, truth)
        c['solved'] += 1
        c['sum_e2'] += e * e
        c['within'] += e <= 0.5
        if q == 1:
            c['fix'] += 1
            c['miss'] += e >= 0.5
    return c


def row(label, method, c):
    return (f"| {label} | `{method}` | {100 * c['fix'] / c['epochs']:.2f} | {100 * c['miss'] / max(c['fix'], 1):.2f} "
            f"| {100 * c['within'] / c['epochs']:.2f} | {math.sqrt(c['sum_e2'] / max(c['solved'], 1)):.2f} |")


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bags', default=os.path.join(here, 'bags'))
    ap.add_argument('--results', default=os.path.join(here, 'results'))
    ap.add_argument('--methods', default='rtk,rnx2rtkp,gnss_fgo,gnss_imu_fgo')
    args = ap.parse_args()
    methods = args.methods.split(',')

    print('| Run | Method | Fix rate % | Miss Fix rate % | 3D <= 0.5 m % | 3D RMS m |')
    print('|---|---|---|---|---|---|')
    totals = {}
    for run in RUNS:
        reference = None
        for method in methods:
            path = os.path.join(args.results, f'{run}_{method}.pos')
            if not os.path.isfile(path):
                continue
            if reference is None:
                reference = read_reference(os.path.join(args.bags, run))
            c = count(reference, read_pos(path, {key for key, _ in reference}))
            print(row(f'`{run}`', method, c), flush=True)
            for group in (run.split('_')[0].capitalize(), 'All'):
                t = totals.setdefault((group, method), dict.fromkeys(c, 0))
                for k in c:
                    t[k] += c[k]
    for group in ('Tokyo', 'Nagoya', 'All'):
        for method in methods:
            if (group, method) in totals:
                print(row(group, method, totals[(group, method)]))
    return 0 if totals else 1


if __name__ == '__main__':
    sys.exit(main())
