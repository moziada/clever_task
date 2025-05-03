# Clever Task

This repository contains a Python-based data pipeline that replicates the "OUTPUT" tab from a referenced spreadsheet. It processes and integrates multiple datasets to generate a structured, formatted Excel output containing housing, population, and income metrics with descriptive blurbs and rankings.

## 📁 Project Structure

```bash
.
├── input_data/
│   ├── CENSUS_MHI_STATE.csv              # Median household income data
│   ├── CENSUS_POPULATION_STATE.tsv       # Population data
│   ├── REDFIN_MEDIAN_SALE_PRICE.csv      # Median home sale price data
│   ├── KEYS.csv                          # Region name mappings
│   ├── key_row.csv                       # List of regions to include in the output
│   └── override_data.csv                 # Optional overrides for hardcoded values
├── output/
│   └── OUTPUT.xlsx                       # Final generated output
└── src/
    ├── generate_output.py                # Main script to generate OUTPUT.xlsx
    ├── utils.py                          # Utility functions for processing
    └── visualization.ipynb              # Plotly-based data visualizations
```

## 📦 Requirements

- Python 3.10.11
- Install dependencies using:

    ```bash
    pip install -r requirements.txt
    ```

## 🚀 How to Run

From the root directory, run the main script:

```bash
python ./src/generate_output.py
```

### Optional Arguments

| Argument                | Type | Default                        | Description                       |
| ----------------------- | ---- | ------------------------------ | --------------------------------- |
| `--population-fname`    | str  | `CENSUS_POPULATION_STATE.tsv`  | Population data file              |
| `--mhi-fname`           | str  | `CENSUS_MHI_STATE.csv`         | Median household income data file |
| `--msp-fname`           | str  | `REDFIN_MEDIAN_SALE_PRICE.csv` | Median sale price file            |
| `--region-keys-fname`   | str  | `KEYS.csv`                     | Region mapping file               |
| `--override-data-fname` | str  | *(optional)*                   | Overrides file for manual entries |
| `--data-dir`            | str  | `input_data`                   | Input directory path              |
| `--output-dir`          | str  | `output`                       | Output directory path             |
| `--output-fname`        | str  | `OUTPUT.xlsx`                  | Name of the final output file     |

### Example

To include manual overrides as seen in the original spreadsheet:

```bash
python ./src/generate_output.py --override-data-fname override_data.csv
```

## 📊 Visualization

Explore data insights using interactive charts built with Plotly in the Jupyter notebook in `./src/visualization.ipynb`.
