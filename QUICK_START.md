# Quick Start Guide - Parameter Format Conversion

## What's New

You can now automatically convert tlog parameters to the par template format when loading tlog files.

## The Simplest Way to Use It

### Method 1: Export to file (one line!)
```python
from tlog2chart_p3.tlog_reader import load_tlog, export_params_to_par_file

# Load tlog
df, unit_info, header_params = load_tlog("my_file.txt")

# Export parameters in par template format
export_params_to_par_file("my_parameters.txt", header_params)
```

Result: File `my_parameters.txt` will contain:
```
General Parameters
2	011001
3	00
4	0
...

Match Parameters
104	5000
105	1000
...
```

### Method 2: Command-line
```bash
python tlog2chart_p3/example_param_conversion.py sample.txt output.txt
```

### Method 3: Get formatted string
```python
from tlog2chart_p3.params_desc import build_param_value_table, convert_params_to_par_template_format

param_rows = build_param_value_table(header_params)
formatted_text = convert_params_to_par_template_format(param_rows)
# Now you can print, email, store, etc.
print(formatted_text)
```

## Where to Find Documentation

- **IMPLEMENTATION_SUMMARY.md** - Overview and technical details
- **PARAMETER_CONVERSION_README.md** - Complete feature documentation  
- **VERIFICATION_NOTES.md** - Format verification and test coverage
- **example_param_conversion.py** - Working example code
- **Testing/par template.txt** - Reference example output format

## What Files Were Changed

### Modified
- `tlog2chart_p3/params_desc.py` - Added conversion function
- `tlog2chart_p3/tlog_reader.py` - Added export function

### Created
- `tlog2chart_p3/example_param_conversion.py` - Example/test script
- IMPLEMENTATION_SUMMARY.md
- PARAMETER_CONVERSION_README.md
- VERIFICATION_NOTES.md
- QUICK_START.md (this file)

## Integration Options

### Option A: No Changes Needed
The feature is ready to use "as-is" from Python code or command line.

### Option B: Add to GUI Menu (Recommended)
Add "Export Parameters" menu item to easily export from GUI:

```python
# In gui_app.py, add to _build_menu():
self.file_menu.add_command(
    label="Export Parameters",
    command=self._on_export_parameters
)

# Add method to class:
def _on_export_parameters(self):
    if not hasattr(self, 'header_params') or not self.header_params:
        messagebox.showwarning("Warning", "No parameters loaded")
        return
    
    output_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt")]
    )
    if output_path:
        from tlog2chart_p3.tlog_reader import export_params_to_par_file
        export_params_to_par_file(output_path, self.header_params)
        messagebox.showinfo("Success", f"Parameters exported")
```

### Option C: Auto-Export with Tlog
Automatically export parameters whenever a tlog is loaded:

```python
# In gui_app.py, _on_loaded() method, add:
from tlog2chart_p3.tlog_reader import export_params_to_par_file
import os

# Auto-export parameters with same base filename
if hasattr(self, 'last_tlog_path') and self.last_tlog_path:
    tlog_base = os.path.splitext(self.last_tlog_path)[0]
    params_file = f"{tlog_base}_parameters.txt"
    export_params_to_par_file(params_file, self.header_params)
    print(f"Parameters exported to: {params_file}")
```

## Feature Highlights

✓ Converts any tlog parameter format to standardized layout  
✓ Works with all unit types (Tykon, Quantum, Triton, Chronos)  
✓ Automatically handles multiple parameter line styles  
✓ No complex configuration needed  
✓ Ready for export, email, documentation  
✓ Can be integrated into GUI in minutes  

## Common Tasks

### Export one tlog
```bash
python tlog2chart_p3/example_param_conversion.py sample.txt params.txt
```

### Batch export all tlogs in folder
```bash
for f in *.txt; do
    python tlog2chart_p3/example_param_conversion.py "$f" "${f%.txt}_params.txt"
done
```

### Use in Python script
```python
from tlog2chart_p3.tlog_reader import load_tlog, export_params_to_par_file

tlog_files = ['file1.txt', 'file2.txt', 'file3.txt']
for tlog_file in tlog_files:
    df, unit_info, header_params = load_tlog(tlog_file)
    output_file = tlog_file.replace('.txt', '_params.txt')
    export_params_to_par_file(output_file, header_params)
    print(f"✓ Exported {output_file}")
```

## Troubleshooting

**Q: Import error - module not found**
```
ImportError: No module named 'tlog2chart_p3'
```
A: Make sure you're running from the project root directory
```bash
cd C:\Users\vhuang01\PycharmProjects\tlog2chart_p3_v1_3
python -m tlog2chart_p3.example_param_conversion ...
```

**Q: No parameters extracted**
```
Found 0 parameter lines
```
A: Make sure the tlog file has parameter sections in the header (starts with //)

**Q: Output doesn't match exactly**
A: Format differences are expected - focus is on content (parameter IDs and values) which are identical

## Next Steps

1. ✓ Review implementation
2. ✓ Try example script: `python tlog2chart_p3/example_param_conversion.py Testing/<tlog_file>.txt`
3. → Test with your actual tlog files from Testing/ folder
4. → (Optional) Integrate "Export Parameters" into GUI menu
5. → (Optional) Test full workflow with your analysis pipeline
6. → Document changes and commit when ready

## Support

For questions or issues, see:
- **IMPLEMENTATION_SUMMARY.md** for overview
- **PARAMETER_CONVERSION_README.md** for detailed documentation
- **example_param_conversion.py** for working code samples

