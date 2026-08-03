# Masai Capstone Project — Books Data Pipeline

## Overview

This repository contains an end-to-end data engineering pipeline written in Python that collects book listings from a public practice website, normalizes the raw HTML-derived values into clean typed records, persists them into a relational SQLite database, and then reports on the stored data using both SQL and Pandas. The project is deliberately structured as a set of small, single-responsibility modules so that each stage of the pipeline — extraction, transformation, loading, and analysis — can be understood, tested, and modified in isolation.

The pipeline follows the classic ETL pattern. Extraction is handled by an HTTP-and-HTML-parsing layer, transformation is handled by a pure-Python cleaning layer with no I/O dependencies, loading is handled by a database manager class that owns the schema and the connection, and analysis is handled by a reporting layer that queries the same database through two independent access paths.

## Project Goals

- Demonstrate a complete, working ETL workflow from a live web source to a queryable relational store.
- Separate concerns cleanly so that scraping logic, business rules, persistence, and reporting never leak into one another.
- Convert messy, string-based web content into strongly typed values suitable for aggregation and comparison.
- Show equivalent analytical results computed two ways — once in SQL and once with Pandas DataFrame operations — to make the relationship between relational algebra and DataFrame manipulation explicit.
- Keep the data store reproducible, so that every run produces a deterministic schema and a fresh dataset rather than accumulating duplicates.

## Repository Structure

- `README.md` — this document, describing the project at the repository level.
- `requirements.txt` — the third-party dependency list for the project, covering the HTTP client, the HTML parser, and the DataFrame library.
- `.gitignore` — patterns for files that should not be tracked in version control.
- `data_pipeline/` — the package containing all pipeline code and its generated database artifact.
- `data_pipeline/main.py` — the orchestration entry point that wires the stages together.
- `data_pipeline/scraper.py` — the extraction layer responsible for network requests and HTML parsing.
- `data_pipeline/cleaner.py` — the transformation layer responsible for type normalization and derived fields.
- `data_pipeline/database.py` — the loading layer responsible for schema management, inserts, and SQL reporting.
- `data_pipeline/analytics.py` — the analysis layer responsible for Pandas-based reads and in-memory joins.
- `data_pipeline/scrape.py` — an earlier single-file version of the workflow, retained as a reference for how the logic looked before it was decomposed into modules.
- `data_pipeline/books.db` — the SQLite database file produced by running the pipeline.
- `data_pipeline/README.md` — module-level notes specific to the pipeline package.

## Pipeline Architecture

### Orchestration Layer

The orchestrator exposes a single `run_pipeline` function that accepts a category limit and a database path, both with sensible defaults. It performs the following sequence:

- Instantiates the database manager, which immediately opens a connection and a cursor against the target SQLite file.
- Resets the schema so that each execution begins from a known-empty state.
- Fetches the list of categories to process, bounded by the configured limit.
- Iterates over each category, scraping its books, cleaning the resulting records, inserting the category row, and inserting the associated book rows keyed to the new category identifier.
- Invokes the SQL reporting routine and the Pandas reporting routine after each category is loaded, so the reports reflect progressively growing data.
- Commits the transaction and closes the connection once every category has been handled.

Categories that yield no books are skipped entirely — no category row is created and no reporting runs for them — which keeps the `categories` table free of empty parents.

### Extraction Layer

The extraction layer targets the public practice site `books.toscrape.com` and is composed of two functions:

- A category discovery function that requests the site's landing page, parses the sidebar navigation list, and returns a list of dictionaries containing each category's display name and its absolute URL. Relative links found in the markup are joined against the base URL, while links that are already absolute are passed through unchanged. The number of categories returned is capped by a caller-supplied limit.
- A per-category scraping function that requests a category page, selects every book article element on it, and extracts four raw fields per book: the star rating (taken from the second CSS class on the rating element), the price string including its currency symbol, the title (preferring the anchor's `title` attribute over its visible text, since the visible text is often truncated), and the availability text.

Both functions raise on non-success HTTP responses rather than silently returning partial data. The extraction layer applies defensive defaults when an expected element is missing — an absent rating becomes the sentinel `"Zero"`, an absent price becomes a zero-valued price string, and absent availability becomes a not-available marker — so that a malformed page degrades a single record rather than aborting the run.

### Transformation Layer

The transformation layer is intentionally pure: it accepts a list of raw dictionaries and returns a list of cleaned dictionaries without touching the network or the database. Its responsibilities are:

- Mapping the textual star ratings to integers on a one-through-five scale, with unrecognized values collapsing to zero so that downstream numeric comparisons remain valid.
- Stripping currency symbols from the price string and parsing the remainder as a floating point value. Both the plain pound sign and its common mojibake form are removed, which guards against the encoding artifacts that frequently appear when scraped bytes are decoded with the wrong codec.
- Deriving a second price field in Indian rupees by applying a fixed conversion rate held as a module-level constant, making the rate easy to locate and adjust in one place.
- Converting the free-text availability string into a boolean stock flag by testing for an exact in-stock match, which yields a field that can be filtered and aggregated reliably.
- Carrying the category name and title through untouched so that the cleaned record remains self-describing.

### Loading Layer

Persistence is encapsulated in a `DatabaseManager` class that owns the connection lifecycle and all SQL statements. Its behavior includes:

- Opening a connection to the configured SQLite path at construction time and holding a reusable cursor.
- Resetting the schema by dropping the `books` table first and the `categories` table second, respecting the dependency direction, and then recreating both tables.
- Defining a `categories` table with an integer primary key and a uniquely constrained category name, which prevents duplicate category rows at the schema level.
- Defining a `books` table with an integer primary key, a title, separate real-valued price columns for pounds and rupees, an integer rating, an integer stock flag, and a foreign key reference back to the parent category.
- Inserting a category and returning the newly generated row identifier so the caller can associate its books with the correct parent.
- Inserting book rows through parameterized statements, which keeps scraped text — including titles containing quotes or other punctuation — from being interpreted as SQL.
- Translating the Python boolean stock flag into the integer representation SQLite expects.
- Exposing explicit commit and close methods so transaction boundaries stay under the orchestrator's control rather than being hidden inside every insert.

### Analysis Layer

Reporting is performed twice over the same data, using two different access mechanisms, so the outputs can be compared directly.

The SQL reporting routine executes a series of representative queries and prints their results:

- A full listing of every category currently stored.
- A filter selecting only books rated above four stars.
- A full listing ordered by ascending pound price.
- A range filter selecting books priced between twenty and forty pounds.
- A bounded listing that returns only the first five rows.
- An inner join between books and categories, restricted to the travel category, returning distinct title and category pairs.

The Pandas reporting routine mirrors each of those queries by reading them into DataFrames through the same live connection, then goes one step further by reproducing the relational join entirely in memory. It merges the books DataFrame with the categories DataFrame on the shared category identifier using an inner join, filters the merged frame down to the travel category, projects only the title and category name columns, and drops duplicate rows. The result is the DataFrame equivalent of the SQL join above, which makes the correspondence between the two paradigms concrete.

## Data Model

- The `categories` table holds one row per scraped category, with a surrogate integer key and a unique name. It acts as the parent in a one-to-many relationship.
- The `books` table holds one row per scraped book, with a surrogate integer key, descriptive and numeric attributes, and a foreign key column pointing at its owning category.
- The relationship is one category to many books, expressed through the foreign key reference, which enables the join used by both the SQL and Pandas reporting paths.
- Ratings are stored as small integers rather than text so that ordering and threshold filters behave numerically.
- Prices are stored as real numbers in two currencies, allowing comparisons in either unit without re-deriving the conversion at query time.
- Stock availability is stored as an integer flag because SQLite has no dedicated boolean type, with the conversion handled at the insertion boundary.

## Design Decisions and Rationale

- **Modular decomposition over a single script.** The original single-file implementation is preserved alongside the modular version, making the refactoring path visible. The modular form allows each stage to be reasoned about and replaced independently.
- **A pure transformation layer.** Because cleaning performs no I/O, it can be exercised directly with hand-constructed input, which is the easiest part of the system to verify.
- **Schema reset on every run.** Dropping and recreating the tables guarantees idempotent output and avoids the duplicate rows that would otherwise accumulate, at the cost of not retaining history across runs.
- **Parameterized SQL everywhere.** Every value that originates from scraped content is bound as a parameter rather than interpolated into a statement string.
- **Constants extracted to module scope.** The rating mapping, the currency conversion rate, and the base site URL are all named constants, so tuning them requires no changes to control flow.
- **Defensive parsing with explicit sentinels.** Missing elements resolve to documented default values instead of raising, so one irregular listing does not terminate an otherwise successful run.
- **Dual reporting paths.** Producing the same answers through SQL and through Pandas serves both as a learning device and as an informal cross-check on correctness.

## Dependencies

- An HTTP client library for issuing the page requests that feed the extraction layer.
- An HTML parsing library for navigating the document tree and selecting the elements that carry book and category data.
- A DataFrame library for the analytical layer, providing the SQL-reading and merge capabilities used in reporting.
- The SQLite database driver and the typing utilities, both of which ship with the Python standard library and therefore require no separate installation.

## Operational Notes

- The pipeline is bounded by a category limit so that a run touches a predictable number of pages rather than the entire site.
- Each category page is fetched once and only its first page of results is processed; the pipeline does not follow pagination links within a category.
- The generated database file lives inside the pipeline package directory and is recreated from scratch whenever the pipeline runs.
- All reporting output is written to standard output as printed text, so a run is self-documenting and its results can be read directly from the console or redirected to a file.
- Because the reporting routines are invoked inside the category loop, the printed output grows in volume as more categories are processed and shows the dataset accumulating over time.

## Possible Extensions

- Following pagination within each category so that every book is captured rather than only the first page.
- Adding retry logic with backoff around the network calls to tolerate transient failures.
- Replacing the hardcoded currency rate with a value fetched from a live exchange-rate source.
- Introducing an upsert strategy so runs can be incremental rather than destructive, preserving history across executions.
- Adding an automated test suite, beginning with the transformation layer since it is dependency-free.
- Replacing printed reporting with structured exports so downstream tools can consume the results programmatically.
- Introducing structured logging in place of print statements to separate diagnostic output from reporting output.