#!/usr/bin/env python3
"""Estimate voltage steps at given events in a log written by read_sensors.py.

A straight line is fitted to the samples before and after each event (leaving a
few seconds around the event out), and both lines are compared at the event time.
This separates a real step from the slow drift of a settling electrode.

Usage: step_analysis.py LOG.csv HH:MM:SS [HH:MM:SS ...] [--window S] [--gap S]
Times are UTC, as in the log.
"""
import argparse
import csv
import datetime
import statistics

MV_PER_PH = 195.4  # nominal slope of the Atlas analog board, from its datasheet end points

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("log")
parser.add_argument("events", nargs="+")
parser.add_argument("--window", type=int, default=60, help="seconds fitted on each side")
parser.add_argument("--gap", type=int, default=4, help="seconds left out on each side")
args = parser.parse_args()

with open(args.log) as f:
    rows = [(datetime.datetime.fromisoformat(r["time_utc"]), float(r["voltage_mv"]))
            for r in csv.DictReader(f)]
t0 = rows[0][0]


def fit(segment):
    xs = [(t - t0).total_seconds() for t, _ in segment]
    ys = [v for _, v in segment]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    intercept = my - slope * mx
    residual_sd = statistics.stdev(y - (intercept + slope * x) for x, y in zip(xs, ys))
    return intercept, slope, residual_sd


for event in args.events:
    h, m, s = map(int, event.split(":"))
    ev = t0.replace(hour=h, minute=m, second=s)
    window, gap = datetime.timedelta(seconds=args.window), datetime.timedelta(seconds=args.gap)
    before = [r for r in rows if ev - window - gap <= r[0] < ev - gap]
    after = [r for r in rows if ev + gap < r[0] <= ev + gap + window]
    x = (ev - t0).total_seconds()
    a1, b1, sd1 = fit(before)
    a2, b2, sd2 = fit(after)
    step = (a2 + b2 * x) - (a1 + b1 * x)
    print(f"{event}: step {step:+.1f} mV ({step / MV_PER_PH:+.3f} pH), "
          f"drift {b1 * 60:.1f} / {b2 * 60:.1f} mV/min before/after, "
          f"residual sd {sd1:.2f} / {sd2:.2f} mV, n {len(before)}/{len(after)}")
