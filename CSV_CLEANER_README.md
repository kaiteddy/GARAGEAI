# CSV Data Cleaning Toolkit

This toolkit provides several powerful scripts for cleaning and improving the quality of CSV data. It leverages multiple data cleaning libraries to provide thorough data cleaning capabilities.

## Scripts Included

1. **master_csv_cleaner.py** - The main script that combines all three cleaning approaches for the most thorough cleaning
2. **clean_csv_data.py** - Uses pandas_dq for data cleaning
3. **clean_with_janitor.py** - Uses PyJanitor for data cleaning
4. **clean_with_autoclean.py** - Uses AutoClean for data cleaning

## Features

These scripts can handle various data quality issues, including:

- Missing values
- Outliers
- Duplicate rows and columns
- Mixed data types
- Skewed distributions
- High cardinality features
- Highly correlated features
- Date/time conversion
- Categorical encoding
- And more!

## Requirements

- Python 3.6+
- pandas
- numpy

The scripts will automatically install the required libraries (pandas_dq, PyJanitor, AutoClean) if they are not already installed.

## Usage

### Master CSV Cleaner (Recommended)

The master cleaner combines all three approaches for the most thorough cleaning:

```bash
python master_csv_cleaner.py input.csv output.csv [--target TARGET_COLUMN] [--method {all,pandas_dq,pyjanitor,autoclean}]
```

Arguments:
- `input.csv`: Path to the input CSV file
- `output.csv`: Path to save the cleaned CSV file
- `--target TARGET_COLUMN`: (Optional) Name of the target column for supervised learning tasks
- `--method`: (Optional) Cleaning method to use. Default is 'all', which uses all three methods

### Individual Cleaners

#### pandas_dq Cleaner

```bash
python clean_csv_data.py input.csv output.csv [--target TARGET_COLUMN] [--html]
```

Arguments:
- `input.csv`: Path to the input CSV file
- `output.csv`: Path to save the cleaned CSV file
- `--target TARGET_COLUMN`: (Optional) Name of the target column
- `--html`: (Optional) Generate HTML report

#### PyJanitor Cleaner

```bash
python clean_with_janitor.py input.csv output.csv [--target TARGET_COLUMN]
```

Arguments:
- `input.csv`: Path to the input CSV file
- `output.csv`: Path to save the cleaned CSV file
- `--target TARGET_COLUMN`: (Optional) Name of the target column

#### AutoClean Cleaner

```bash
python clean_with_autoclean.py input.csv output.csv
```

Arguments:
- `input.csv`: Path to the input CSV file
- `output.csv`: Path to save the cleaned CSV file

## Examples

### Clean a CSV file using all methods

```bash
python master_csv_cleaner.py data.csv cleaned_data.csv
```

### Clean a CSV file using only pandas_dq

```bash
python master_csv_cleaner.py data.csv cleaned_data.csv --method pandas_dq
```

### Clean a CSV file with a target column

```bash
python master_csv_cleaner.py data.csv cleaned_data.csv --target target_column_name
```

## Logs

Each script generates a log file in the current directory:
- `master_cleaner.log`
- `csv_cleaner.log`
- `janitor_cleaner.log`
- `autoclean_cleaner.log`

These logs contain detailed information about the cleaning process, including any errors or warnings.

## Notes

- For large datasets, the cleaning process may take some time.
- The scripts attempt to read CSV files with multiple encodings (utf-8, latin1, ISO-8859-1, cp1252).
- The AutoClean library generates its own log file (`autoclean.log`).
