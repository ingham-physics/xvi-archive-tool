# XVI Archive Tool

This tool runs on an XVI system to detect patients who have finished treatment and
this data can be deleted or archived.

This code was written using Python 2.7 to enable it to be compiled and run on
legacy Windows XP systems. Ideally this will be updated to Python 3 as XVI systems
are migrated to later versions of Windows.

## Running the code

Ensure Python 2.7 and pip are installed. Install requirements first:

```bash
pip install -r requirements.txt
```

and then run the tool to display the GUI:

```bash
python run.py
```

You can run the tool as a scheduled task and avoid showing the GUI:

```bash
python run.py --auto-run
```

Before you can successfully run the code, centre specific OIS queries should be added in the marked locations
of the `database.py` file.

While various OIS databases should be compatible, MOSAIQ has only been tested with this
code. Adjustments may be required to support other OIS databases.

## Glossary

- OIS: Oncology Information System
- MRN: Medical Record Number. May be referred to as Unique Patient Identifier or similar based on your OIS

## Author

- **Phillip Chlap** - [phillip.chlap@unsw.edu.au](phillip.chlap@unsw.edu.au)
