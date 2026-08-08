# Module 1 - Data Pipeline (Books Web Scraping to SQLite)

This module builds a complete data pipeline that takes live data from a website
and ends with a queryable database. The website used is books.toscrape.com which
is a practice site made specifically for scraping, so no login and no API key is
needed.

The pipeline has five stages and they always run in the same order.

Scrape the pages, clean the raw text into proper data types, convert the price
from pounds to rupees, load everything into a normalized SQLite database, and
finally query that database using both SQL and pandas.

Everything is inside one file called scrape.py. Running that one file does all
five stages with no manual steps in between.

---

## Note - The Markdown Used in This File

Before the sections begin, a short note on how this document itself is written.
Only two pieces of markdown formatting are used anywhere below, code blocks and
tables. Both are written with plain characters and nothing else is needed.

One detail to get right first. Code blocks are written with the backtick
character, which is the key above Tab and to the left of the number 1. It is not
the apostrophe or the single quote character.

Code blocks

Three backticks open the block, the language name goes right after them with no
space, and three backticks on their own line close it.

````
```python
def getMedian(values):
    return sorted(values)[len(values) // 2]
```
````

That renders as this.

```python
def getMedian(values):
    return sorted(values)[len(values) // 2]
```

| Rule | Detail |
| --- | --- |
| Opening line | Three backticks, then the language name, no space between them |
| Language names used in this README | python, bash, sql |
| Closing line | Three backticks alone, nothing after them |
| If the language is left out | It still renders as code, only without the colour highlighting |
| Spacing | Leave a blank line before the opening and after the closing line |

For a single word inside a sentence, use one backtick on each side instead of
three. That is how column names are marked up in running text.

Tables

A table is made of pipe characters. The second row, the one made of dashes, is
required. It is what tells markdown that these lines are a table rather than
ordinary text.

```
| Column | Type | Meaning |
| --- | --- | --- |
| price_gbp | REAL | Price in pounds |
| rating | INTEGER | 1 to 5 |
```

That renders as this.

| Column | Type | Meaning |
| --- | --- | --- |
| price_gbp | REAL | Price in pounds |
| rating | INTEGER | 1 to 5 |

| Rule | Detail |
| --- | --- |
| First row | The column headings |
| Second row | One set of three dashes per column, separated by pipes, mandatory |
| Third row onward | The data rows |
| Column count | Every row needs the same number of pipe separators |
| Alignment | Three dashes is left aligned, colon dashes colon is centred, dashes colon is right aligned |
| Spacing | The pipes do not have to line up in the source file, the table renders the same either way |

---

## Section 1 - Files in this Folder

| File | What it is |
| --- | --- |
| scrape.py | The whole pipeline. One file, runs end to end. |
| books.db | The SQLite database created by the script. 174 books in 10 categories. |
| query_outputs.md | Every SQL query and its output, rewritten on every run. |
| README.md | This file. |

---

## Section 2 - How to Run It

Step 1. Activate the virtual environment.

```bash
source ../.venv/bin/activate
```

Step 2. Install the libraries.

```bash
pip install -r ../requirements.txt
```

Step 3. Run the script from inside this folder. This matters because the output
paths in the script are relative paths, not absolute ones.

```bash
cd data_pipeline
python3 scrape.py
```

The libraries used are listed below.

| Library | Why it is needed | Comes with Python? |
| --- | --- | --- |
| requests | Downloads the HTML of each page over HTTP | No, install it |
| beautifulsoup4 | Reads that HTML and lets us select tags | No, install it |
| pandas | Reads query results into DataFrames and does the merge | No, install it |
| sqlite3 | Creates the database, inserts rows, runs queries | Yes, built in |

The script drops and recreates books.db from scratch every time, rewrites
query_outputs.md, and prints its progress to the console. A full run takes about
a minute depending on the network speed.

---

## Section 3 - What Exactly Gets Scraped

The assignment asks for a minimum of 60 rows across at least 3 categories. This
pipeline goes well past that.

| Item | Required | What this pipeline does |
| --- | --- | --- |
| Number of rows | 60 minimum | 174 rows |
| Number of categories | 3 minimum | 10 categories |
| Pages per category | Not specified | The first listing page only, up to 20 books |

The category links are picked up from the sidebar of the home page with this
selector.

```python
categories = soup.select("div.side_categories ul li ul li a")[1:11]
```

The slice [1:11] does two things at once. It skips index 0 and it stops at 10
categories.

**Design decision: index 0 is skipped on purpose.** That first link is the
catalogue-wide "Books" link, which is not a real category. It is the parent that
holds every book on the site. If it were included it would insert a meaningless
parent row in the categories table and duplicate books that already appear under
their true category.

**Design decision: only the first listing page of each category is read, and
pagination links are not followed.** This is why a large category like Fiction
contributes 20 rows here instead of its full 65 rows on the site. The 60 row
target is already met without pagination and the pipeline mechanics being
demonstrated are exactly the same either way.

For each book on a page the script captures five things.

| Field captured | Where it comes from in the HTML |
| --- | --- |
| title | The title attribute of the anchor inside h3 |
| price | The p tag with class price_color |
| star rating | The second class name on the p tag with class star-rating |
| availability | The p tag with class instock availability |
| category | The sidebar link text, carried down from the loop |

**Design decision: the title is read from the title attribute, not from the
visible text of the link.**

```python
title = book.find("h3").find("a")["title"]
```

On listing pages the visible link text is cut short with an ellipsis, so a long
title shows as "The Bachelor Girl's Guide to ..." instead of the full name. The
title attribute always holds the complete untruncated title, which is why it is
the one used.

**Design decision: the encoding is set by hand rather than left to requests.**

```python
response.encoding = "utf-8"
```

The site sends utf-8 content but does not declare it in the headers, so requests
guesses latin-1 instead. Without this line the pound sign arrives as the two
character mojibake Â£ and prices look broken.

---

## Section 4 - Cleaning and Type Conversion

Everything that comes out of HTML is text. A price is the string "£51.77" and a
rating is the word "Three". None of that can be sorted, filtered or averaged
correctly, so each field is converted into a proper type.

| Column | Type after cleaning | Raw value example | Cleaned value |
| --- | --- | --- | --- |
| title | text | "Sharp Objects" | "Sharp Objects" |
| price_gbp | float | "£47.82" | 47.82 |
| price_inr | float | derived | 5045.010 |
| rating | int 1 to 5 | "Four" | 4 |
| in_stock | bool | "In stock (19 available)" | True |
| availability | text | "In stock" | "In stock" |
| category | text | "Mystery" | "Mystery" |

Price cleaning strips the currency symbol and parses what is left.

```python
raw_price = raw_price.replace("Â£", "").replace("£", "").strip()
book_data["price_gbp"] = float(raw_price)
```

**Design decision: both the plain £ and the mojibake Â£ are removed.** The
encoding fix in Section 3 should mean Â£ never appears, but removing both costs
nothing and makes the parser safe even if the encoding fix is ever lost.

Rating cleaning maps the English word to a number through a dictionary.

```python
rating_map = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
book_data["rating"] = rating_map.get(book_data["rating"])
```

**Design decision: the rating is stored as an integer, not as the original
word.** This matters because of how sorting works. As text, "Four" sorts before
"One" and "Three" sorts before "Two", which is alphabetical nonsense. As
integers, 4 sorts after 3 correctly, and a filter like rating > 4 becomes
possible. That exact filter is used in query 2.

**Design decision: stock is detected with a substring check, not an exact string
match.**

```python
availability = book_data["availability"].lower()
if "in stock" in availability:
    book_data["in_stock"] = True
```

The site renders availability in more than one wording. A book listing page may
say "In stock" while a product page says "In stock (19 available)". An exact
comparison would mark the second one as out of stock, which is wrong. A
substring check handles both.

**Design decision: the original availability text is stored as well, in its own
column, even though in_stock is derived from it.** This means the boolean can
always be traced back to the exact wording the site gave. In the current
database every one of the 174 rows has availability equal to "In stock", so
in_stock is 1 for all 174 rows.

There is also a warning branch for wording that mentions neither state.

```python
if "out of stock" not in availability and "unavailable" not in availability:
    print(f"[warn] unrecognised availability ... - treated as out of stock")
```

This avoids silently defaulting an unknown phrase to False. The row still gets
False, but the run output says so.

---

## Section 5 - Handling Rows That Fail to Parse

Real scraping hits messy pages. A tag may be missing, a price may be blank, a
rating class may say something unexpected. The pipeline is written so that none
of this crashes the run.

**Design decision: the work happens in two passes rather than one.**

Pass 1 tries every conversion and marks whatever fails as None instead of
raising an error. Pass 2 goes back over those rows and either repairs them or
discards them according to a fixed policy.

The policy is in this table.

| What failed | What the pipeline does | Why that is the right call |
| --- | --- | --- |
| price is missing or not a number | Fill price_gbp with the median | The rest of the row, title, category, rating, stock, is still correct and useful. Throwing away the whole record would shrink and bias the catalogue. The median is used instead of the mean because a few very expensive books would drag a mean upwards. |
| star rating is missing or outside One to Five | Fill rating with the median | Same reasoning as price. The median is cast to int so the column stays a valid 1 to 5 integer instead of becoming something like 3.5. |
| The product card itself is unreadable, no h3 anchor with a title | Drop the row | The title is the identity of the record. A book with no title cannot be joined, deduplicated or reported on, so there is nothing worth imputing. |
| A field failed and there is no median to borrow, meaning every row in that category failed | Drop the row | There is no defensible value to fill in, and inserting NULL would break the typed column requirement. |

Two important points about how the median is built.

**Design decision 1: the median is category-local, not catalogue-wide.** It is
computed only from the successfully parsed rows inside the same category. This
matters because prices vary a lot between categories. The current medians show
why.

| Category | Median price GBP |
| --- | --- |
| Womens Fiction | 43.58 |
| Fiction | 41.86 |
| Childrens | 35.19 |
| Classics | 35.01 |
| Historical Fiction | 34.31 |
| Sequential Art | 32.95 |
| Romance | 30.06 |
| Philosophy | 29.93 |
| Religion | 28.42 |
| Mystery | 27.03 |

A broken Mystery price replaced with 27.03 is much closer to the truth than
replacing it with a catalogue-wide figure near 34. The gap between the highest
and lowest category median is about 16.55 pounds, which is large relative to the
prices themselves.

**Design decision 2: every repair is logged.** Imputations print a [impute]
line, drops print a [drop] line, and strange availability text prints a [warn]
line. So the run output states exactly which rows were changed and why.

On a clean scrape of the live site none of these lines appear at all. All 174
rows parse correctly. The behaviour was tested by deliberately corrupting the
scraped HTML, which produced logged imputations on the affected rows while the
run still finished with a complete database.

The median itself is written by hand rather than imported.

```python
def getMedian(values):
    ordered_values = sorted(values)
    total = len(ordered_values)
    middle = total // 2
    if total % 2 == 1:
        return ordered_values[middle]
    return (ordered_values[middle - 1] + ordered_values[middle]) / 2
```

For an odd count it returns the single middle value. For an even count it
returns the average of the two middle values.

---

## Section 6 - Currency Conversion

Each price is stored twice, once in pounds and once in rupees.

The rate used is fixed.

1 GBP = 105.50 INR

```python
for book in books_data:
    book["price_inr"] = book["price_gbp"] * 105.50
```

**Design decision: the rate is a fixed constant, not a live API lookup.** It is
an artificial constant defined by the project for this assignment. It is not a
live rate and not a historical rate for any particular date. Because it is a
constant, no external API call is made and no network access is needed for this
stage, and every run produces the same numbers, which keeps the output
reproducible.

Worked examples from the current database.

| Title | price_gbp | Calculation | price_inr |
| --- | --- | --- | --- |
| Sharp Objects | 47.82 | 47.82 x 105.50 | 5045.010 |
| In a Dark, Dark Wood | 19.63 | 19.63 x 105.50 | 2070.965 |
| The Past Never Ends | 56.50 | 56.50 x 105.50 | 5960.750 |
| A Murder in Time | 16.64 | 16.64 x 105.50 | 1755.520 |
| Patience | 10.16 | 10.16 x 105.50 | 1071.880 |

**Design decision: both currencies are kept in the table**, so a value can be
read in either unit at query time without redoing the multiplication in SQL.

---

## Section 7 - Database Schema

The database is normalized into two tables that share a primary key to foreign
key relationship.

```sql
categories(category_id   INTEGER PRIMARY KEY,
           category_name TEXT UNIQUE)

books(book_id      INTEGER PRIMARY KEY,
      title        TEXT,
      price_gbp    REAL,
      price_inr    REAL,
      rating       INTEGER,
      in_stock     INTEGER,
      availability TEXT,
      category_id  INTEGER REFERENCES categories(category_id))
```

Column by column, the books table looks like this.

| Column | Type | Meaning |
| --- | --- | --- |
| book_id | INTEGER PRIMARY KEY | Auto assigned row id |
| title | TEXT | Full untruncated book title |
| price_gbp | REAL | Price in pounds after cleaning |
| price_inr | REAL | Price in rupees, gbp times 105.50 |
| rating | INTEGER | 1 to 5 |
| in_stock | INTEGER | 1 for true, 0 for false |
| availability | TEXT | Original wording from the site |
| category_id | INTEGER FOREIGN KEY | Points at categories.category_id |

The design decisions behind this schema are as follows.

**Design decision: the schema is normalized rather than one flat table.**
Normalization removes repetition. The word "Mystery" is stored once in the
categories table rather than 20 times inside the books table. Across all 10
categories that is 174 repeated strings collapsed into 10 stored strings, and
renaming a category later is a single row update rather than a bulk update.

**Design decision: the constraint lives in the schema, not in the Python code.**
The UNIQUE constraint on category_name stops duplicate parent rows from being
inserted at the schema level instead of relying on the Python code to remember.

**Design decision: integer join keys are used rather than joining on the
category name string.** Comparing integers is cheaper to index and faster to
execute than comparing text.

**Design decision: in_stock is stored as an INTEGER**, because SQLite has no
dedicated boolean type. Python's True and False convert to 1 and 0 at the
insertion boundary, which is why the query output shows 1 rather than True.

**Design decision: the tables are dropped and recreated on every run.**

```python
cursor.execute("DROP TABLE IF EXISTS books")
cursor.execute("DROP TABLE IF EXISTS categories")
```

This guarantees reproducible output and stops duplicate rows piling up across
runs. The trade off is that no history is kept between executions. That is
acceptable here because the site is the source of truth and can be rescraped at
any time.

**Design decision: every scraped value is passed as a bound parameter, never
glued into the SQL string.**

```python
cursor.execute("INSERT INTO books (title, price_gbp, price_inr, rating, in_stock, availability, category_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
(book["title"], book["price_gbp"], ...))
```

This matters with this dataset specifically. Titles here contain apostrophes,
for example "The Bachelor Girl's Guide to Murder". String interpolation would
break the statement on that apostrophe, and in general would open the door to
SQL injection. Parameter binding sends the value separately from the statement,
so punctuation inside a title can never be read as SQL.

---

## Section 8 - What the Loaded Data Looks Like

These are the actual contents of books.db after a clean run.

Overall totals.

| Measure | Value |
| --- | --- |
| Total book rows | 174 |
| Distinct titles | 174, so no duplicates |
| Categories | 10 |
| Cheapest book | 10.16 GBP |
| Most expensive book | 59.99 GBP |
| Average price | 34.72 GBP |
| Rows in stock | 174 out of 174 |

Rows per category, with price and rating summaries.

| id | Category | Books | Min GBP | Max GBP | Avg GBP | Avg rating |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Mystery | 20 | 10.69 | 59.48 | 32.79 | 2.90 |
| 2 | Historical Fiction | 20 | 16.62 | 55.55 | 35.38 | 2.95 |
| 3 | Sequential Art | 20 | 10.16 | 54.63 | 32.92 | 2.95 |
| 4 | Classics | 19 | 14.82 | 58.63 | 36.55 | 2.47 |
| 5 | Philosophy | 11 | 15.94 | 58.11 | 33.56 | 2.36 |
| 6 | Romance | 20 | 12.87 | 59.99 | 31.04 | 2.80 |
| 7 | Womens Fiction | 17 | 13.73 | 57.36 | 36.79 | 3.12 |
| 8 | Fiction | 20 | 10.60 | 55.84 | 37.70 | 3.45 |
| 9 | Childrens | 20 | 12.96 | 58.08 | 36.40 | 2.65 |
| 10 | Religion | 7 | 21.87 | 57.49 | 32.57 | 3.14 |

Six categories have exactly 20 rows, which is the full first page. Four have
fewer because those categories simply do not have 20 books on the site.
Classics has 19, Womens Fiction has 17, Philosophy has 11 and Religion has 7.
No rows were lost to dropping or errors, these are the real category sizes.

Rating distribution across all 174 books.

| Rating | Number of books | Share |
| --- | --- | --- |
| 1 star | 43 | 24.7 percent |
| 2 star | 28 | 16.1 percent |
| 3 star | 38 | 21.8 percent |
| 4 star | 36 | 20.7 percent |
| 5 star | 29 | 16.7 percent |

The ratings on this practice site are close to random, which is expected because
they are generated test data rather than real reader ratings. Fiction has the
highest average rating at 3.45 and Philosophy the lowest at 2.36, but with only
11 books in Philosophy that difference is not meaningful.

Two counts that the queries in the next section depend on.

| Filter | Matching rows |
| --- | --- |
| rating > 4, meaning 5 star only | 29 |
| price_gbp between 20 and 40 | 70 |

---

## Section 9 - The SQL Queries

Six queries are run. **Design decision: they run once, after the whole dataset
has been loaded and committed, not inside the scraping loop.** That ordering
matters. A query run inside the loop would report against a half filled database
and give a different answer on each iteration.

Here are the six queries and the clauses each one demonstrates.

| # | Query | Clauses shown |
| --- | --- | --- |
| 1 | Every category in the lookup table | SELECT, LIMIT |
| 2 | Books rated above 4 | SELECT, WHERE, LIMIT |
| 3 | Books sorted by ascending price | ORDER BY, LIMIT |
| 4 | Books priced between 20 and 40 pounds | WHERE, BETWEEN, LIMIT |
| 5 | The first five books in the table | LIMIT |
| 6 | Distinct Mystery titles with their category name | DISTINCT, JOIN, WHERE, LIMIT |

The assignment asks for SELECT and WHERE, ORDER BY, LIMIT, DISTINCT, either IN
or BETWEEN, and at least one JOIN. The mapping is shown below.

| Required clause | Covered by |
| --- | --- |
| SELECT and WHERE | Query 2 |
| ORDER BY | Query 3 |
| LIMIT | All six queries |
| DISTINCT | Query 6 |
| IN or BETWEEN | Query 4 uses BETWEEN, so IN is not needed |
| JOIN | Query 6 |

The full SQL of the join query, which is the most involved one, is below.

```sql
SELECT DISTINCT title, category_name FROM books
JOIN categories ON books.category_id = categories.category_id
WHERE categories.category_name = 'Mystery' LIMIT 5
```

This walks the foreign key relationship. It starts from the books table, follows
category_id into the categories table to pick up the readable name, filters on
that name, and removes any repeated title with DISTINCT.

**Design decision: every query carries LIMIT 5.** This keeps the saved output
short enough to read at a glance. It also means that what query_outputs.md
records is each query's complete result set, not a trimmed version of a longer
one. Nothing is cut after the fact.

Note the difference between the row counts. Query 4 has 70 matching rows in the
database but LIMIT 5 shows five of them. That is the LIMIT doing its job, not a
data problem.

Each query is executed with sqlite3 through cursor.execute and fetchall, printed
to the console, and appended to query_outputs.md with its SQL text and its rows
rendered as a table with column headers. The headers come from cursor.description.

```python
pd.DataFrame(rows, columns=[column[0] for column in cursor.description])
```

Three of the six queries are additionally read back into DataFrames with
pd.read_sql, which satisfies the requirement to read at least two query results
back into pandas. Those three are the rating filter, the limit query and the
join.

---

## Section 10 - SQL and Pandas Giving the Same Answer

The join query is produced twice through two completely independent routes, and
then the two results are compared.

Route 1 is SQL. pd.read_sql runs the JOIN inside SQLite and hands back a
DataFrame.

```python
read_sql_join = pd.read_sql(join_sql, con=sqllite_connection)
```

Route 2 is pandas only. DataFrames are built from the in-memory scraped records
and joined with pd.merge. No SQL is involved at any point in this route.

```python
merged_books_cat = pd.merge(books_df, categories_df, on="category_id", how="inner")
merge_join = (merged_books_cat[merged_books_cat["category_name"] == "Mystery"]
              [["title", "category_name"]]
              .drop_duplicates()
              .head(5)
              .reset_index(drop=True))
```

**Design decision: the category id is carried onto the in-memory records.** That
is what makes route 2 possible, and it is one line back in the insert loop.

```python
book["category_id"] = category_id
```

The category id that SQLite assigned at insert time is copied onto the in-memory
record. Without that, the pandas side would have no key to merge on and would
have to fall back to joining on the category name string.

The two routes line up clause for clause.

| SQL clause | pandas equivalent |
| --- | --- |
| JOIN categories ON books.category_id = categories.category_id | pd.merge(books_df, categories_df, on="category_id", how="inner") |
| WHERE category_name = 'Mystery' | Boolean mask on the category_name column |
| DISTINCT | drop_duplicates() |
| LIMIT 5 | head(5) |
| Row numbering of the result | reset_index(drop=True) |

**Design decision: reset_index is applied before comparing.** It is needed for a
technical reason. After filtering, the pandas rows keep their original index
positions from the merged frame, while the SQL result comes back numbered from
0. Without resetting, the values would match but the comparison would still
report False because the indexes differ.

The two results are printed side by side in one frame and compared.

```python
is_identical = read_sql_join.equals(merge_join)
```

The comparison reports True. Both routes return the same five Mystery titles in
the same order.

| Row | Title | Category |
| --- | --- | --- |
| 0 | Sharp Objects | Mystery |
| 1 | In a Dark, Dark Wood | Mystery |
| 2 | The Past Never Ends | Mystery |
| 3 | A Murder in Time | Mystery |
| 4 | The Murder of Roger Ackroyd (Hercule Poirot #4) | Mystery |

This comparison is also written into query_outputs.md, so the match can be seen
without rerunning the pipeline.

One maintenance note. The two routes are kept in step by hand. If the SQL join
is ever edited, for example changing Mystery to Romance, the pandas chain has to
be edited to match or the equals check will start reporting False.

---

## Section 11 - Summary of Assignment Requirements

| Requirement | Where it is done | Status |
| --- | --- | --- |
| Scrape at least 60 rows | Section 3 | 174 rows |
| Cover at least 3 categories | Section 3 | 10 categories |
| Clean fields into proper types | Section 4 | float, int, bool, text |
| Handle rows that fail to parse | Section 5 | Median impute or drop, all logged |
| Currency conversion | Section 6 | 1 GBP = 105.50 INR |
| Normalized schema, two tables with a key relationship | Section 7 | categories and books |
| Insert cleaned data with sqlite3 | Section 7 | Parameter bound inserts |
| SELECT, WHERE, ORDER BY, LIMIT, DISTINCT, IN or BETWEEN | Section 9 | All covered |
| At least one JOIN | Section 9 | Query 6 |
| Read at least two query results into pandas | Section 9 | Three queries read back |
| Save every query and its output | Section 9 | query_outputs.md |
