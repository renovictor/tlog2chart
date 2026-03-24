"""Command-line entry point for tlog2chart."""

from __future__ import annotations

import argparse
import sys

from .parser import DEFAULT_MESSAGE_TYPES, TlogParser
from .plotter import TlogPlotter


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tlog2chart",
        description="Plot EVC tlog (MAVLink telemetry log) data as charts.",
    )
    p.add_argument(
        "tlog",
        help="Path to the .tlog file to process.",
    )
    p.add_argument(
        "-o",
        "--output",
        default="charts",
        help=(
            "Output directory (or file path when plotting a single message type). "
            "Defaults to 'charts/'."
        ),
    )
    p.add_argument(
        "-m",
        "--messages",
        metavar="MSG",
        nargs="+",
        default=DEFAULT_MESSAGE_TYPES,
        help=(
            "MAVLink message types to plot (space-separated). "
            f"Defaults to: {' '.join(DEFAULT_MESSAGE_TYPES)}."
        ),
    )
    p.add_argument(
        "--show",
        action="store_true",
        help="Show interactive plot windows in addition to saving files.",
    )
    p.add_argument(
        "--list-messages",
        action="store_true",
        help="Parse the tlog file and print the available message types, then exit.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns an exit code."""
    args = _build_parser().parse_args(argv)

    try:
        parser = TlogParser(args.tlog, message_types=args.messages)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Parsing {args.tlog} …")
    data = parser.parse()

    if not data:
        print("No matching messages found in the tlog file.", file=sys.stderr)
        return 1

    if args.list_messages:
        for msg_type in sorted(data.keys()):
            print(f"  {msg_type}: {len(data[msg_type])} records")
        return 0

    print(f"Found message types: {', '.join(sorted(data.keys()))}")

    plotter = TlogPlotter(data)
    figures = plotter.plot(output=args.output, show=args.show)

    if figures:
        print(f"Saved {len(figures)} chart(s) to '{args.output}'.")
    else:
        print("No charts were generated.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
