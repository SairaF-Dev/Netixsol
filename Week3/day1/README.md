# SQL Foundations for Data Science

This repo contains the deliverables for the "SQL Foundations for Data Science" task: setting up PostgreSQL, importing the Superstore Sales dataset, and learning SQL basics (SELECT, WHERE, ORDER BY, GROUP BY, aggregate functions).

## Contents

- `concept_check.md` — answers to the 10 concept-check questions
- `setup.sql` — all SQL commands used to create the database, create the table, and import the data
- `screenshots/` — proof of each step (database created, table created, data imported, table structure, query results)
- `dataset/superstore_dataset.csv` — the Superstore Sales dataset used for this task (original source: [Kaggle](https://www.kaggle.com/datasets/vivek468/superstore-dataset-final))

## Setup Steps

### 1. Install PostgreSQL and pgAdmin

Download and install PostgreSQL from [postgresql.org/download](https://www.postgresql.org/download/) — the installer includes pgAdmin 4 (the GUI tool used to manage the database) as one of its components. During installation, set a password for the `postgres` superuser and keep the default port (5432).

### 2. Download the dataset

Download the Superstore Sales dataset from [Kaggle](https://www.kaggle.com/datasets/vivek468/superstore-dataset-final). The file downloads as an Excel file — open it and save it as CSV (`File → Save As → CSV (Comma delimited)`) before importing.

### 3. Create the database

In pgAdmin, open a Query Tool connected to the `postgres` database and run:

```sql
CREATE DATABASE super_store_db;
```

### 4. Set the date format

Connect to `super_store_db` and run:

```sql
ALTER DATABASE super_store_db SET datestyle = 'ISO, MDY';
```

This ensures dates like `6/16/2016` (M/D/YYYY format) are parsed correctly during import. Close and reopen the Query Tool afterward so the new connection picks up this setting.

### 5. Create the table

Run the `CREATE TABLE` statement from `setup.sql`. It defines all 21 columns with appropriate data types, a `PRIMARY KEY` on `row_id`, `NOT NULL` constraints on essential fields, and `CHECK` constraints on `quantity` (must be > 0) and `discount` (must be between 0 and 1).

### 6. Import the CSV data

Run the `COPY` command from `setup.sql`, adjusting the file path to point to wherever you've placed `superstore_dataset.csv` on your own machine (e.g., if you cloned this repo to `C:/projects/sql-foundations`, the path would be `C:/projects/sql-foundations/dataset/superstore_dataset.csv`). `COPY` requires a full, absolute path — it does not accept a relative path like `./dataset/...`.

Key options used:
- `HEADER` — skips the header row (column names) instead of importing it as data
- `ENCODING 'WIN1252'` — matches the encoding Excel saves CSV files in on Windows
- `QUOTE '"'` and `ESCAPE '"'` — correctly handles product names containing quote characters (e.g., `72"H x 36"W`)

> Note: If `COPY` gives a "Permission denied" error, it's because `COPY` runs on the PostgreSQL server process, which may not have access to your user folder. Either grant the `NETWORK SERVICE` account Read permission on the folder (Properties → Security → Edit), or use pgAdmin's GUI **Import/Export Data** tool instead, which handles file access client-side.

### 7. Verify the import

Run the verification queries at the bottom of `setup.sql`:

```sql
SELECT COUNT(*) FROM superstore_sales;              -- should return 9994
SELECT * FROM superstore_sales LIMIT 10;             -- preview first 10 rows
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'superstore_sales';               -- view table structure
```

**Alternate way to view table structure (without SQL):** In pgAdmin, right-click the `superstore_sales` table in the left sidebar → **Properties...** → **Columns** tab. This shows the same information (column name, data type, length, NOT NULL, Primary Key) in a GUI table, and can also be used to edit the structure directly.

## Notes

- Database name is `super_store_db` and table name is `superstore_sales`.
- All SQL commands are available in `setup.sql` for easy re-run on a fresh setup.
