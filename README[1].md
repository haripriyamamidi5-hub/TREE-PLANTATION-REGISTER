# TREE PLANTATION REGISTER — Mini Project

## Overview
A Python command-line application for registering plantation activity and monitoring follow-up survival checks. It stores data locally in JSON and maintains a CSV copy.

## Requirements
- Python 3.10 or later
- Windows 10/11, macOS or Linux
- Matplotlib (installed by the launcher)

## Run on Windows
1. Extract the ZIP file.
2. Open `tree_plantation_register`.
3. Double-click `run_windows.bat`, or open CMD in this folder.
4. Run `python -m pip install -r requirements.txt`
5. Run `python tree_register.py`

## Run on macOS/Linux
Run `python3 -m pip install -r requirements.txt` and `python3 tree_register.py`.

## Menu
1 Add plantation record | 2 Survival follow-up | 3 View records | 4 Search/filter
5 Executive summary | 6 Generate charts | 7 Export reports | 8 Import CSV
9 Overdue warnings | 10 Load 40 sample records (empty register only) | 0 Save and exit

## Data files
- `data/trees.json`: primary local data store
- `data/trees.csv`: spreadsheet-compatible copy
- `charts/`: generated chart images
- `exports/`: summary, audit log and CSV import error report

## Import duplicate rule
CSV rows are treated as duplicates when tree name, quantity, location, plantation date and planted-by values all match (case-insensitive text comparison).

## Run automated tests
`python -m unittest discover -s tests -v`

## Important
The included data folder starts empty. Back up any existing project data before replacing project files. The sample data is demonstration data, not a field survey.
