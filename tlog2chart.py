"""tlog2chart – Convert EVC tlog files to charts.

Usage
-----
    python tlog2chart.py <tlog_file> [<tlog_file> ...] [options]

Options
-------
    -o, --output-dir DIR    Directory for generated PNG files (default: current
                            directory, or a sibling directory named after the
                            tlog file when a single file is given).
    --show                  Also display charts interactively (requires GUI).
    -h, --help              Show this help message and exit.

Examples
--------
    # Plot a single tlog file:
    python tlog2chart.py sample_data/sample_tlog.txt

    # Plot multiple files into a specific output directory:
    python tlog2chart.py logs/*.txt -o charts/
"""

import argparse
import os
import sys

import tlog_parser
import plotter


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tlog2chart",
        description="Convert EVC tlog files to charts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "tlog_files",
        metavar="TLOG_FILE",
        nargs="+",
        help="One or more EVC tlog text files to process.",
    )
    p.add_argument(
        "-o", "--output-dir",
        metavar="DIR",
        default=None,
        help="Directory for generated PNG files.  Defaults to a directory "
             "named '<stem>_charts' next to the tlog file.",
    )
    p.add_argument(
        "--show",
        action="store_true",
        default=False,
        help="Display charts interactively after saving (requires a GUI).",
    )
    return p


def _default_output_dir(tlog_path: str) -> str:
    stem = os.path.splitext(os.path.basename(tlog_path))[0]
    parent = os.path.dirname(os.path.abspath(tlog_path))
    return os.path.join(parent, f"{stem}_charts")


def main(argv=None) -> int:
    args = _build_arg_parser().parse_args(argv)

    exit_code = 0
    for tlog_path in args.tlog_files:
        if not os.path.isfile(tlog_path):
            print(f"ERROR: file not found: {tlog_path}", file=sys.stderr)
            exit_code = 1
            continue

        output_dir = args.output_dir or _default_output_dir(tlog_path)

        print(f"Parsing  : {tlog_path}")
        try:
            tlog = tlog_parser.parse_file(tlog_path)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: failed to parse {tlog_path}: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        n = len(tlog.records)
        sn = tlog.metadata.serial_number or "(unknown)"
        print(f"  Records : {n}  |  SN: {sn}")
        if n == 0:
            print("  WARNING: No charging records found – skipping chart generation.")
            continue

        print(f"  Output  : {output_dir}")
        try:
            generated = plotter.plot_tlog(tlog, output_dir=output_dir, show=args.show)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: chart generation failed for {tlog_path}: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        for path in generated:
            print(f"    Saved : {path}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
