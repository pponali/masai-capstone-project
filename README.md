# Masai Capstone Project

A multi-module capstone repository. Module 1 lives in [`data_pipeline/`](data_pipeline/) and implements a scrape → clean → convert → store → query pipeline over [books.toscrape.com](https://books.toscrape.com).

## Repository Structure

| Path | Description |
| --- | --- |
| `data_pipeline/scrape.py` | Module 1 pipeline — scraping, cleaning, SQLite loading and the SQL/pandas queries. |
| `data_pipeline/books.db` | The generated SQLite database (174 books across 10 categories). |
| `data_pipeline/query_outputs.md` | Every executed query with its output. |
| `data_pipeline/README.md` | Module 1 notes — scope, cleaning policy, schema and design decisions. |
| `requirements.txt` | Third-party dependencies: `requests`, `BeautifulSoup4`, `pandas`. |

## Install

Run these from the repository root.

1. **Create a virtual environment** (Python 3.9 or newer)
   ```bash
   python3 -m venv .venv
   ```

2. **Activate it**
   ```bash
   source .venv/bin/activate
   ```
   On Windows, use `.venv\Scripts\activate` instead.

3. **Install the dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   Everything else the pipeline uses — `sqlite3`, `urllib` — ships with the standard library.

## Run

Change into the module directory first, because the script writes `books.db` and `query_outputs.md` to the current working directory.

```bash
cd data_pipeline
python3 scrape.py
```

The run is self-contained and needs no manual steps: it scrapes the site, drops and recreates the database from scratch, executes the queries, prints everything to the console, and rewrites `query_outputs.md`. It takes roughly a minute depending on network speed, and requires an internet connection since the data is scraped live.

To confirm the result:

```bash
sqlite3 data_pipeline/books.db "SELECT COUNT(*) FROM books;"   # 174
```

## Design Decisions

Module-level decisions — the scrape scope, the median-imputation policy for unparseable rows, the fixed `1 GBP = 105.50 INR` conversion, the two-table schema and the SQL/pandas equivalence check — are documented in [`data_pipeline/README.md`](data_pipeline/README.md).
