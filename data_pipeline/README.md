# Books Scraper Data Pipeline

A robust end-to-end Python data pipeline that scrapes book catalog data from [Books to Scrape](https://books.toscrape.com), cleans and transforms the data, stores it in a normalized SQLite relational database, and performs analytical queries and merges using Pandas.

---

## Technical & Architectural Decisions

### 1. Web Scraping Technology: `requests` + `BeautifulSoup4`
* **Decision**: Use `requests` for fetching HTTP pages and `BeautifulSoup4` with `html.parser` for HTML extraction, rather than browser automation tools like Playwright or Selenium.
* **Rationale**: 
  * `books.toscrape.com` is a static HTML site rendered on the server side.
  * Lightweight `HTTP GET` requests execute orders of magnitude faster than headless browsers, consuming minimal CPU and RAM.
  * Zero browser driver dependencies make the pipeline highly portable and CI/CD-friendly.

---

### 2. Database Schema Design: Normalized Relational Database (2NF/3NF)
* **Decision**: Create two separate, normalized SQLite tables (`categories` and `books`) linked via a Foreign Key (`category_id`).
  * **`categories` Table**: `(category_id INTEGER PRIMARY KEY, category_name TEXT UNIQUE)`
  * **`books` Table**: `(book_id INTEGER PRIMARY KEY, title TEXT, price_gbp REAL, price_inr REAL, rating INTEGER, in_stock INTEGER, category_id INTEGER REFERENCES categories(category_id))`
* **Rationale**:
  * **Eliminates Redundancy**: Storing category names once in a lookup table avoids repeating identical string names across thousands of book records.
  * **Data Integrity**: Foreign key constraints guarantee referential integrity between books and their respective categories.
  * **Storage & Index Efficiency**: Integer join keys (`category_id`) allow faster indexing and join execution compared to string joins.

---

### 3. Data Cleaning & Transformation Pipeline
* **Rating Normalization**:
  * **Decision**: Convert text ratings (`"One"`, `"Two"`, ..., `"Five"`) into numeric integers (`1`, `2`, ..., `5`) using a dictionary lookup map.
  * **Rationale**: Numeric integers enable direct mathematical calculations (e.g., averages, filters like `rating > 4`) without string parsing overhead in database queries.
* **Currency Cleaning & Conversion**:
  * **Decision**: Clean encoding artifacts (`Â£`, `£`) from price strings, cast to `float`, and compute a derived column `price_inr` using `1 GBP = 105.50 INR`.
  * **Rationale**: Preserves both original currency (`price_gbp`) for auditing and localized currency (`price_inr`) for business reporting.
* **Boolean Flag Conversion**:
  * **Decision**: Transform text availability string (`"In stock"`) to boolean `1`/`0` (`True`/`False`).
  * **Rationale**: Simplifies conditional logic in SQL queries (`WHERE in_stock = 1`) and reduces memory footprint in Pandas.

---

### 4. Data Processing: SQL & Pandas Integration
* **Decision**: Use `sqlite3` for SQL execution and `pandas` (`pd.read_sql` and `pd.merge`) for in-memory DataFrames.
* **Rationale**:
  * Demonstrates both database-level querying (`SQL JOIN`, `ORDER BY`, `WHERE`) and application-level data manipulation in Pandas.
  * `pd.merge()` reproduces SQL joins in memory, enabling downstream integration with data science and machine learning workflows without requiring repeated database reads.

---

## Pipeline Execution Overview

```
               [ Website: books.toscrape.com ]
                              │
                              ▼
            [ HTTP GET via requests & BeautifulSoup ]
                              │
                              ▼
            [ Data Cleaning & Field Normalization ]
             - Rating: String ➔ Integer (1..5)
             - Price: String ➔ Float (GBP)
             - Currency: GBP ➔ INR Conversion
             - Availability: String ➔ Boolean (1/0)
                              │
                              ▼
           [ SQLite Storage (books.db - Normalized) ]
             - Table 1: categories (category_id, category_name)
             - Table 2: books (book_id, title, price_gbp, price_inr, ...)
                              │
                              ▼
        [ Pandas Analytics (pd.read_sql & pd.merge) ]
```

---

## How to Run

1. **Activate Virtual Environment**:
   ```bash
   source ../venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r ../requirements.txt
   ```

3. **Run the Data Pipeline**:
   ```bash
   python3 scrape.py
   ```
