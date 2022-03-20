# XVI Archive Tool

This tool runs on an XVI system to detect patients who have finished treatment and
thei data can be deleted or archived.

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
