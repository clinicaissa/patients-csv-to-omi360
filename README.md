# Patients CSV to OMI360
Script to convert a generated CSV of patients in the current database into a CSV compatible with [OMI360.org](http://omi360.org) medical software

## Requirements
This script has been tested with Python 3.6 and requires `Pandas` library to work

You can install the requirements with `pip` automatically

```bash
pip install -r requirements.txt
```

## Usage
Usage is very simple:
```bash
python transform.py <input_file>
```

To see how the input file must be formatted, check the code constants
