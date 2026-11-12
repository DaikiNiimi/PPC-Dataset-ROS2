#!/usr/bin/env python3
"""Draw the figures of the README from the bags and the .pos solutions.

    python3 tools/plot_results.py [--bags bags] [--results results] [--out fig]

    routes.png         reference trajectory of each run
    error_cdf.png      cumulative distribution of the 3D error (Tokyo, Nagoya, all runs)
    tracks_<city>.png  result of every epoch, drawn at its reference position

Epoch matching and the 3D error are those of tools/evaluate.py.
"""
import argparse
import math
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluate import A, F, RUNS, read_pos, read_reference  # noqa: E402

METHODS = ['rtk', 'gnss_fgo', 'gnss_imu_fgo']
SERIES = {'rtk': '#2a78d6', 'gnss_fgo': '#eb6834', 'gnss_imu_fgo': '#1baf7a'}
WITHIN, OUTSIDE, MISS = '#2a78d6', '#b9b8b1', '#eb6834'
INK, MUTED, GRID = '#0b0b0b', '#52514e', '#e4e3df'
LIMIT = 0.5  # m

plt.rcParams.update({
    'font.size': 9, 'axes.edgecolor': GRID, 'axes.labelcolor': MUTED, 'text.color': INK,
    'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.titlesize': 10, 'axes.titleweight': 'bold',
    'figure.facecolor': 'white', 'axes.facecolor': 'white', 'savefig.dpi': 130,
})


def enu(ecef):
    """East and north (m) of ECEF positions (n x 3) about their first point."""
    x, y, z = ecef[0]
    e2 = F * (2.0 - F)
    lon, p = math.atan2(y, x), math.hypot(x, y)
    lat = math.atan2(z, p * (1.0 - e2))
    for _ in range(5):
        n = A / math.sqrt(1.0 - e2 * math.sin(lat) ** 2)
        lat = math.atan2(z + e2 * n * math.sin(lat), p)
    d = ecef - ecef[0]
    east = -math.sin(lon) * d[:, 0] + math.cos(lon) * d[:, 1]
    north = (-math.sin(lat) * math.cos(lon) * d[:, 0] - math.sin(lat) * math.sin(lon) * d[:, 1]
             + math.cos(lat) * d[:, 2])
    return east, north


def load(bags, results):
    """{run: (keys, east, north, {method: (3D error or inf, Q or 0) per reference epoch})}."""
    data = {}
    for run in RUNS:
        reference = read_reference(os.path.join(bags, run))
        keys = [k for k, _ in reference]
        east, north = enu(np.array([p for _, p in reference]))
        per_method = {}
        for method in METHODS:
            path = os.path.join(results, f'{run}_{method}.pos')
            if not os.path.isfile(path):
                continue
            solution = read_pos(path, set(keys))
            error, q = np.full(len(keys), np.inf), np.zeros(len(keys), int)
            for i, (key, truth) in enumerate(reference):
                if key in solution:
                    q[i], error[i] = solution[key][0], math.dist(solution[key][1], truth)
            per_method[method] = (error, q)
        data[run] = (np.array(keys), east, north, per_method)
        print(run, flush=True)
    return data


def frame(ax, east, north, margin=0.07):
    """Square, equal-scale axes without ticks around a trajectory."""
    half = (0.5 + margin) * max(np.ptp(east), np.ptp(north))
    ce, cn = (east.min() + east.max()) / 2, (north.min() + north.max()) / 2
    ax.set_xlim(ce - half, ce + half)
    ax.set_ylim(cn - half, cn + half)
    ax.set_aspect('equal', adjustable='box')
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ax.spines.values():
        side.set_color(GRID)


def scale_bar(ax, length):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x, y = x0 + 0.04 * (x1 - x0), y0 + 0.04 * (y1 - y0)
    ax.plot([x, x + length], [y, y], color=INK, lw=1.5, solid_capstyle='butt')
    ax.text(x + length / 2, y + 0.02 * (y1 - y0), f'{length:g} m', ha='center', va='bottom', fontsize=8, color=MUTED)


def bar_length(east, north):
    span = max(np.ptp(east), np.ptp(north))
    return next(v for v in (2000, 1000, 500, 200, 100, 50) if v <= 0.3 * span)


def plot_routes(data, out):
    fig, axes = plt.subplots(2, 3, figsize=(10, 7.1))
    for ax, run in zip(axes.flat, RUNS):
        keys, east, north, _ = data[run]
        ax.plot(east, north, color=SERIES['rtk'], lw=1.6, solid_joinstyle='round')
        ax.plot(east[0], north[0], 'o', ms=7, mfc=INK, mec='white', mew=1.5)
        frame(ax, east, north)
        scale_bar(ax, bar_length(east, north))
        length = float(np.hypot(np.diff(east), np.diff(north)).sum())
        ax.set_title(run, loc='left')
        ax.set_title(f'{length / 1000:.1f} km, {(keys[-1] - keys[0]) / 1000:.0f} s', loc='right',
                     fontsize=8.5, fontweight='normal', color=MUTED)
    fig.legend(handles=[Line2D([], [], marker='o', ls='', ms=7, mfc=INK, mec='white', mew=1.5, label='start')],
               loc='lower center', frameon=False, fontsize=9)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(os.path.join(out, 'routes.png'))
    plt.close(fig)


def plot_cdf(data, out):
    groups = [('Tokyo', RUNS[:3]), ('Nagoya', RUNS[3:]), ('All runs', RUNS)]
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.7), sharey=True)
    x = np.logspace(-2, 2, 400)
    for ax, (title, runs) in zip(axes, groups):
        handles = []
        for method in METHODS:
            errors = np.concatenate([data[r][3][method][0] for r in runs if method in data[r][3]] or [np.empty(0)])
            if not errors.size:
                continue
            ordered = np.sort(errors)
            ax.plot(x, 100.0 * np.searchsorted(ordered, x, side='right') / errors.size,
                    color=SERIES[method], lw=2, solid_joinstyle='round', solid_capstyle='round')
            share = 100.0 * np.count_nonzero(errors <= LIMIT) / errors.size
            handles.append(Line2D([], [], color=SERIES[method], lw=2, label=f'{method}  {share:.1f} %'))
        ax.axvline(LIMIT, color=MUTED, lw=1)
        ax.set_xscale('log')
        ax.set_xlim(0.01, 100)
        ax.set_ylim(0, 100)
        ax.set_xticks([0.01, 0.1, 1, 10, 100], ['0.01', '0.1', '1', '10', '100'])
        ax.set_xticks([LIMIT], ['0.5'], minor=True)
        ax.tick_params(axis='x', which='minor', length=3, labelsize=8)
        ax.grid(True, which='major', color=GRID, lw=1)
        ax.set_axisbelow(True)
        ax.tick_params(length=0)
        ax.set_title(title, loc='left')
        ax.set_xlabel('3D error (m)')
        legend = ax.legend(handles=handles, title='within 0.5 m', loc='lower right', frameon=False, fontsize=8.5,
                           title_fontsize=8.5, handlelength=1.6)
        legend._legend_box.align = 'left'
        legend.get_title().set_color(MUTED)
    axes[0].set_ylabel('Reference epochs within the error (%)')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'error_cdf.png'))
    plt.close(fig)


def plot_tracks(data, city, out):
    runs = [r for r in RUNS if r.startswith(city)]
    fig, axes = plt.subplots(len(runs), len(METHODS), figsize=(10.5, 3.6 * len(runs) + 0.4), squeeze=False)
    for row, run in zip(axes, runs):
        _, east, north, per_method = data[run]
        for ax, method in zip(row, METHODS):
            frame(ax, east, north)
            ax.set_title(method if run == runs[0] else '', loc='left')
            if method not in per_method:
                continue
            error, q = per_method[method]
            within, miss = error <= LIMIT, (q == 1) & (error >= LIMIT)
            ax.scatter(east[~within], north[~within], s=2.2, color=OUTSIDE, lw=0, rasterized=True)
            ax.scatter(east[within], north[within], s=2.2, color=WITHIN, lw=0, rasterized=True)
            ax.scatter(east[miss], north[miss], s=11, color=MISS, lw=0, rasterized=True)
            fix = np.count_nonzero(q == 1)
            ax.set_title(f'within 0.5 m {100 * within.mean():.1f} %, Miss Fix {100 * miss.sum() / max(fix, 1):.2f} %',
                         loc='right', fontsize=8, fontweight='normal', color=MUTED)
        row[0].set_ylabel(run, fontsize=10, fontweight='bold', color=INK)
        scale_bar(row[0], bar_length(east, north))
    fig.legend(handles=[
        Line2D([], [], marker='o', ls='', ms=6, color=WITHIN, label='3D error within 0.5 m'),
        Line2D([], [], marker='o', ls='', ms=6, color=OUTSIDE, label='3D error above 0.5 m or no solution'),
        Line2D([], [], marker='o', ls='', ms=7, color=MISS,
               label='FIX with a 3D error of 0.5 m or more (Miss Fix)')],
        loc='upper center', ncol=3, frameon=False, fontsize=9, handletextpad=0.3, columnspacing=1.8)
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.35 / fig.get_figheight()))
    fig.savefig(os.path.join(out, f'tracks_{city}.png'))
    plt.close(fig)


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bags', default=os.path.join(here, 'bags'))
    ap.add_argument('--results', default=os.path.join(here, 'results'))
    ap.add_argument('--out', default=os.path.join(here, 'fig'))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    data = load(args.bags, args.results)
    plot_routes(data, args.out)
    plot_cdf(data, args.out)
    for city in ('tokyo', 'nagoya'):
        plot_tracks(data, city, args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
