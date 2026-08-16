#!/usr/bin/env python3
"""
Get the current position (latitude, longitude, accuracy/precision) via GeoClue2.

Requirements:
    sudo apt install gir1.2-geoclue-2.0 python3-gi
    GeoClue2 daemon (package "geoclue-2.0") must be installed and running.
"""

import argparse
import json
import sys

import gi
gi.require_version("Geoclue", "2.0")
from gi.repository import GLib, Geoclue

def get_current_position(app_id="my-python-app",
                          accuracy_level=Geoclue.AccuracyLevel.EXACT,
                          timeout_seconds=15,
                          max_accuracy_meters=None,
                          on_update=None):
    loop = GLib.MainLoop()
    result = {}
    error_holder = {}
    simple_holder = {}

    def meets_threshold(location):
        if max_accuracy_meters is None:
            return True
        accuracy = location.get_property("accuracy")
        return accuracy is not None and accuracy <= max_accuracy_meters

    def capture(location):
        result["latitude"] = location.get_property("latitude")
        result["longitude"] = location.get_property("longitude")
        result["accuracy"] = location.get_property("accuracy")
        if on_update is not None:
            on_update(dict(result))

    def on_location_notify(simple, param):
        location = simple.get_location()
        if location is None:
            return
        capture(location)
        if meets_threshold(location):
            loop.quit()

    def on_client_ready(source, res, user_data=None):
        try:
            simple = Geoclue.Simple.new_finish(res)
        except GLib.Error as e:
            error_holder["error"] = e
            loop.quit()
            return

        simple_holder["simple"] = simple

        location = simple.get_location()
        if location is not None:
            capture(location)
            if meets_threshold(location):
                loop.quit()
                return

        simple.connect("notify::location", on_location_notify)

    def on_timeout():
        if "latitude" not in result:
            error_holder["error"] = TimeoutError(
                f"No location fix received within {timeout_seconds}s"
            )
        loop.quit()
        return False

    GLib.timeout_add_seconds(timeout_seconds, on_timeout)

    Geoclue.Simple.new(app_id, accuracy_level, None, on_client_ready)

    loop.run()

    if "error" in error_holder:
        raise error_holder["error"]

    return result

def parse_args():
    parser = argparse.ArgumentParser(
        description="Get the current position via GeoClue2."
    )
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=15,
        metavar="SECONDS",
        help="max time to wait for a location fix (default: 15)",
    )
    parser.add_argument(
        "-a", "--accuracy",
        type=float,
        default=600,
        metavar="METERS",
        help=("keep waiting for fixes until accuracy is reached"),
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="print every position fix as it's acquired, not just the final one",
    )
    parser.add_argument(
        "-vo", "--verbose-stdout",
        action="store_true",
        help=("print intermediate positions to stdout"),
    )
    return parser.parse_args()

def main():
    args = parse_args()
    if args.verbose_stdout:
        args.verbose = True

    def print_update(fix):
        stream = sys.stdout if args.verbose_stdout else sys.stderr
        print(json.dumps(fix), file=stream)

    try:
        loc = get_current_position(
            accuracy_level=Geoclue.AccuracyLevel.EXACT,
            timeout_seconds=args.timeout,
            max_accuracy_meters=args.accuracy,
            on_update=print_update if args.verbose else None,
        )
    except Exception as e:
        print(f"Failed to get location: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps({
        "lat": loc["latitude"],
        "lon": loc["longitude"],
        "accuracy": loc["accuracy"],
    }))

if __name__ == "__main__":
    main()
