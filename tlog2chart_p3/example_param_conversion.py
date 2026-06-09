#!/usr/bin/env python3
"""
Example: Convert tlog parameters to par template format

This script demonstrates how to extract parameters from a tlog file
and convert them to the par template format.

Usage:
    python example_param_conversion.py <tlog_file> <output_par_file>

Example:
    python example_param_conversion.py sample.txt parameters_extracted.txt
"""

import sys
from pathlib import Path

from tlog_reader import load_tlog, export_params_to_par_file
from params_desc import build_param_value_table, convert_params_to_par_template_format


def main():
    if len(sys.argv) < 2:
        print("Usage: python example_param_conversion.py <tlog_file> [output_par_file]")
        print("\nExample:")
        print("  python example_param_conversion.py sample.txt parameters_extracted.txt")
        sys.exit(1)
    
    tlog_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "parameters_extracted.txt"
    
    # Check if tlog file exists
    if not Path(tlog_file).exists():
        print(f"Error: File '{tlog_file}' not found")
        sys.exit(1)
    
    try:
        print(f"Loading tlog: {tlog_file}")
        df, unit_info, header_params = load_tlog(tlog_file)
        
        print(f"✓ Loaded {len(df)} data rows")
        print(f"✓ Unit Info: {unit_info.get('UnitType', 'Unknown')}")
        print(f"✓ Found {len(header_params)} parameter lines")
        
        # Method 1: Use the convenience function to export to file
        print(f"\nExporting parameters to: {output_file}")
        export_params_to_par_file(output_file, header_params)
        print(f"✓ Parameters exported successfully")
        
        # Method 2: Get formatted string for display/further processing
        param_rows = build_param_value_table(header_params)
        formatted_params = convert_params_to_par_template_format(param_rows)
        
        print("\n" + "="*60)
        print("PARAMETERS IN PAR TEMPLATE FORMAT")
        print("="*60)
        print(formatted_params)
        print("="*60)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

