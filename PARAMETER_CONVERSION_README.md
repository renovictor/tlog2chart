Parameter Format Conversion: Tlog → Par Template
===================================================

Overview
--------
When loading a tlog file, this feature converts the extracted parameters 
from raw tlog format into the standardized par template format for consistency 
and easier analysis/export.

Format Comparison
-----------------

RAW TLOG FORMAT:
    // General Parameters
    2 011001, 3 00, 4 0, 6 1, 7 0, ...
    
    // Match Parameters
    104 5000, 105 1000, 107 0, ...

PAR TEMPLATE FORMAT:
    General Parameters
    2     011001
    3     00
    4     0
    6     1
    7     0
    
    Match Parameters
    104   5000
    105   1000
    107   0

Functions Available
-------------------

1. `convert_params_to_par_template_format(param_rows: List[Tuple[str, int, str]]) -> str`
   Location: tlog2chart_p3/params_desc.py
   
   Converts a list of (section, param_id, value) tuples into formatted par template text.
   
   Usage:
   ```python
   from tlog2chart_p3.params_desc import build_param_value_table, convert_params_to_par_template_format
   
   param_rows = build_param_value_table(header_params)
   formatted_text = convert_params_to_par_template_format(param_rows)
   print(formatted_text)
   ```

2. `export_params_to_par_file(output_path: str, header_params: List[Tuple[str, str]])`
   Location: tlog2chart_p3/tlog_reader.py
   
   Convenience function to directly export parameters to a .txt file in par template format.
   
   Usage:
   ```python
   from tlog2chart_p3.tlog_reader import load_tlog, export_params_to_par_file
   
   df, unit_info, header_params = load_tlog("sample.txt")
   export_params_to_par_file("output_params.txt", header_params)
   ```

Usage Examples
--------------

EXAMPLE 1: Export parameters to file when loading tlog
   
   from tlog2chart_p3.tlog_reader import load_tlog, export_params_to_par_file
   
   # Load tlog file
   df, unit_info, header_params = load_tlog("my_tlog.txt")
   
   # Export parameters to par template format
   export_params_to_par_file("my_parameters.txt", header_params)
   
   # The output file will contain all parameters nicely formatted by section


EXAMPLE 2: Get formatted parameters as string
   
   from tlog2chart_p3.tlog_reader import load_tlog
   from tlog2chart_p3.params_desc import build_param_value_table, convert_params_to_par_template_format
   
   df, unit_info, header_params = load_tlog("my_tlog.txt")
   
   # Convert to table format
   param_rows = build_param_value_table(header_params)
   
   # Convert to par template format string
   formatted = convert_params_to_par_template_format(param_rows)
   
   # Use formatted string for display, export, etc.
   print(formatted)
   # or save to file
   with open("params.txt", "w") as f:
       f.write(formatted)


EXAMPLE 3: Command-line usage
   
   cd tlog2chart_p3_v1_3
   python tlog2chart_p3/example_param_conversion.py sample.txt output_params.txt


Output Format Details
---------------------

The par template format groups parameters by section:

- Section names appear on their own line (e.g., "General Parameters")
- Empty line separates sections
- Each parameter appears as: param_id[TAB]value
- Parameters are sorted by ID within each section

Section Order (preserved):
  1. General Parameters
  2. HF Match Params (for Quantum/products with dual matching)
  3. LF Match Params (for Quantum/products with dual matching)
  4. Match Parameters (for single-match units like Tykon/Triton)
  5. Generator Parameters
  6. PIDs
  7. Any other sections (sorted alphabetically)

Implementation Details
---------------------

The conversion process:

1. **Extract from tlog**: `extract_parameter_blocks()` parses raw lines from tlog header
   Result: List[Tuple[str, str]] = [(section_name, raw_line), ...]

2. **Parse parameter pairs**: `parse_param_pairs_from_line()` extracts ID/value pairs
   Supports formats:
   - Quantum style: "1,70.0,2,1111,3,0,..."
   - Tykon style: "2 011001, 3 00, 4 0"
   - Doc style: "101: 10.0 ms = ..."

3. **Build table**: `build_param_value_table()` creates structured rows
   Result: List[Tuple[str, int, str]] = [(section, param_id, value), ...]

4. **Format output**: `convert_params_to_par_template_format()` creates final text
   Result: str with proper sections and formatting

Supported Unit Types
--------------------

The conversion works for all supported unit types:
- Tykon0527
- Tykon1213
- Quantum2013
- Triton2060
- Chronos 2.0
- Chronos 2.1

Each unit type has specific parameter sets that are automatically organized 
into the correct sections.

Integration with GUI
--------------------

To integrate parameter export into the main GUI application:

1. After loading a tlog file in the GUI, call:
   ```python
   export_params_to_par_file(output_path, header_params)
   ```

2. Add a menu item "Export Parameters" that prompts for output file and calls the function

3. Or automatically export to a default location like:
   ```python
   output_path = os.path.join(
       os.path.dirname(tlog_path),
       os.path.splitext(os.path.basename(tlog_path))[0] + "_params.txt"
   )
   export_params_to_par_file(output_path, header_params)
   ```

Testing
-------

To test the parameter conversion:

1. Use the example script:
   python tlog2chart_p3/example_param_conversion.py <tlog_file>

2. Compare output with:
   - Original par template files
   - EVC parameter lists from device console output

3. Verify parameter count and values match expected values for the unit type

