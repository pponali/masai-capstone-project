# Module 1 — Data Pipeline

An end-to-end pipeline that scrapes live product data from [books.toscrape.com](https://books.toscrape.com), cleans it into properly typed columns, enriches it with the project's fixed-rate currency conversion, loads it into a normalized SQLite database, and then queries that database with both SQL and pandas.

The workflow needs: **scrape → clean → convert → store → query**. The source site is built for scraping so no credentials are required.

---

## Contents

| File | Description |
| --- | --- |
| `scrape.py` | The entire pipeline. Runs end to end with no manual steps. |
| `books.db` | The generated SQLite database — 174 books across 10 categories. |
| `query_outputs.md` | Every executed query with its output, rewritten on each run. |
| `README.md` | This document. |

---

## How to Run

1. **Activate the virtual environment**
   ```bash
   source ../.venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r ../requirements.txt
   ```
   The pipeline needs `requests`, `beautifulsoup4` and `pandas`. `sqlite3` and `statistics` ship with the standard library.

3. **Run the pipeline** — from inside this folder, since the output paths are relative
   ```bash
   cd data_pipeline
   python3 scrape.py
   ```

The script is self-contained. It drops and recreates `books.db` from scratch on every run, rewrites `query_outputs.md`, and prints its progress and query results to the console. There is no manual copy-pasting at any stage, and a run takes roughly a minute depending on network speed.

---

## Scope of the Scrape

The assignment requires a minimum of 60 rows across at least three categories. This pipeline covers:

* **10 categories**, taken from the sidebar navigation.
* **174 book rows** in the final dataset, comfortably above the 60-row floor.
* **The first listing page of each category** — up to 20 books per category. Pagination links are not followed, which is why a large category such as Fiction contributes 20 rows rather than its full 65. The row target is met without it, and the pipeline mechanics being demonstrated are identical either way.
* **The catalogue-wide "Books" link is excluded.** It is the entire catalogue rather than a category, so including it would insert a meaningless parent row and duplicate books that already appear under their real category.
* **Per book the script captures** the title, the price as listed in GBP, the star rating as text, the availability text as listed, and the category name.

Titles are read from the anchor's `title` attribute rather than its visible text, because the visible text is truncated with an ellipsis on listing pages.

---

## Cleaning and Type Conversion

Each raw field is converted to a proper type:

* **`price_gbp` (float)** — the currency symbol is stripped and the remainder parsed as a float. Both the plain `£` and its mojibake form `Â£` are removed.
* **`rating` (int, 1–5)** — the text rating (`One`…`Five`) is mapped through a dictionary to an integer, so ordering and threshold filters behave numerically instead of alphabetically.
* **`in_stock` (bool)** — derived from the availability text by matching the substring `in stock`, so a page rendering `In stock (19 available)` is treated identically to one rendering a bare `In stock`.
* **`availability` (text)** — the original as-listed string is *also* stored, so the derived flag can always be traced back to what the site actually said.
* **`price_inr` (float)** — see the conversion section below.

### Handling Rows That Fail to Parse

The pipeline never crashes on messy input. Parsing happens in two passes: the first attempts every conversion and marks failures as `None`, and the second repairs or discards those rows according to a fixed policy.

| Failure | Policy | Justification |
| --- | --- | --- |
| `price` missing or non-numeric | **Median-impute** `price_gbp` | The row's other fields — title, category, rating, stock — are still correct and useful for aggregate analysis, so discarding the whole record would bias the catalogue. The median is used instead of the mean so that a handful of extreme prices cannot drag the replacement value. |
| `star_rating` absent or outside `One`…`Five` | **Median-impute** `rating` | Same reasoning. The median is cast to `int`, keeping the column a valid 1–5 integer rather than a float such as `3.5`. |
| The product card is unreadable (no `<h3><a title=…>`) | **Drop the row** | The title is the record's identity. A book with no title cannot be joined, deduplicated or reported on, so there is nothing worth imputing. |
| A field fails **and** no median exists (every row in the category failed) | **Drop the row** | There is no defensible value to borrow, and inserting `NULL` would break the typed-column requirement. |

Two further notes on this policy:

* **The median is category-local.** It is computed from the successfully parsed rows within the same category, because prices vary materially between categories — a Mystery median is a far closer estimate for a broken Mystery price than a catalogue-wide one.
* **Every repair is logged.** Imputations, drops and unrecognised availability text each print a `[impute]`, `[drop]` or `[warn]` line, so the run output shows exactly which rows were altered and why. On a clean scrape of the live site none of these lines appear — all 174 rows parse cleanly. The behaviour was verified by deliberately corrupting the scraped HTML, which produced logged imputations on the affected rows while the run still completed with a full database.

---

## Currency Conversion

`price_inr` is derived from `price_gbp` using the project's fixed baseline rate:

> **1 GBP = 105.50 INR**

This is an artificial, project-defined constant for this assignment — not a live or historical market rate. It carries no date reference, requires no external API call and needs no network access. Both currencies are stored so that a value can be read in either unit without re-deriving the conversion at query time.

---

## Database Schema

The database is normalized into two tables sharing a primary/foreign key relationship:

```sql
categories(category_id INTEGER PRIMARY KEY,
           category_name TEXT UNIQUE)

books(book_id     INTEGER PRIMARY KEY,
      title       TEXT,
      price_gbp   REAL,
      price_inr   REAL,
      rating      INTEGER,
      in_stock    INTEGER,
      availability TEXT,
      category_id INTEGER REFERENCES categories(category_id))
```

Design decisions behind it:

* **Normalization eliminates redundancy.** Each category name is stored once in a lookup table instead of being repeated across every one of its books, and the `UNIQUE` constraint prevents duplicate parents at the schema level.
* **Integer join keys** make the join cheaper to index and execute than a string join would be.
* **`in_stock` is stored as an integer** because SQLite has no dedicated boolean type; the conversion happens at the insertion boundary.
* **The schema is dropped and recreated on every run**, which guarantees reproducible output and prevents duplicate rows accumulating across runs. The trade-off is that no history is retained between executions.
* **Every scraped value is bound as a parameter**, never interpolated into a statement string, so titles containing quotes or other punctuation cannot be interpreted as SQL.

---

## SQL Queries

Six queries run **once**, after the full dataset has been loaded and committed — not inside the scraping loop, so each one reports against the complete database rather than a partially filled one. Between them they cover every required clause:

| # | Query | Clauses demonstrated |
| --- | --- | --- |
| 1 | Every category in the lookup table | `SELECT`, `LIMIT` |
| 2 | Books rated above four | `SELECT` / `WHERE`, `LIMIT` |
| 3 | Books by ascending price | `ORDER BY`, `LIMIT` |
| 4 | Books priced between £20 and £40 | `WHERE`, `BETWEEN`, `LIMIT` |
| 5 | The first five books in the table | `LIMIT` |
| 6 | Distinct Mystery titles with their category name | `DISTINCT`, `JOIN`, `WHERE`, `LIMIT` |

The required clause list is `SELECT`/`WHERE`, `ORDER BY`, `LIMIT`, `DISTINCT` and `IN` **or** `BETWEEN`, plus at least one `JOIN`. `BETWEEN` in query 4 covers the fifth of those, so `IN` is not needed.

Every query carries `LIMIT 5`, which keeps the saved output short enough to read at a glance. Because of that, what `query_outputs.md` records is each query's *complete* result — nothing is trimmed after the fact.

Each query is executed with `sqlite3` via `cursor.execute` / `fetchall`, printed to the console, and appended to `query_outputs.md` with its query string and its rows rendered as a table with column headers. Three of them — the rating filter, the limit query and the join — are additionally read back into DataFrames with `pd.read_sql`, satisfying the "read at least two query results back into pandas" requirement.

---

## SQL and Pandas Equivalence

The join query is produced twice, by two independent routes:

* **Via SQL** — `pd.read_sql` executes the `JOIN` against SQLite.
* **Via pandas** — `pd.merge` joins DataFrames built directly from the in-memory scraped records, with no SQL involved at any point. The category id assigned at insert time is carried on the in-memory records, which is what lets the merge reproduce the relational join exactly.

The pandas side mirrors the SQL clause for clause: `drop_duplicates()` for the `DISTINCT`, a boolean mask for the `WHERE`, and `head(5)` for the `LIMIT 5`. If the SQL join is ever edited, the pandas chain has to be edited to match, or the two stop agreeing.

Both results are printed side by side in a single frame and compared with `.equals()`, which reports **`True`**. The comparison is written to `query_outputs.md` as well, so the match is visible without re-running the pipeline.

