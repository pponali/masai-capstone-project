# first import the required libraries
# pip3 install requests BeautifulSoup4
# pyrefly: ignore [missing-import]
import requests
from bs4 import BeautifulSoup
import sqlite3
import pandas as pd
from statistics import median
from pathlib import Path
from urllib.parse import urljoin

DB_PATH = Path(__file__).parent / "books.db"
OUTPUT_DIR = Path(__file__).parent / "query_outputs"

#one row per query, saved to query_outputs/queries.csv at the end.
query_log = []


def getConnCursor():
    """single place that opens the sqlite connection and returns it with its cursor."""
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    return connection, cursor


def run_query(label, sql):
    """run the query, print it, and save its output as a csv file."""
    connection, cursor = getConnCursor()
    rows = cursor.execute(sql).fetchall()
    result = pd.read_sql(sql, con=connection)
    connection.close()

    output_file = f"{len(query_log) + 1}_{label}.csv"
    result.to_csv(OUTPUT_DIR / output_file, index=False)
    query_log.append({"label": label, "sql": sql, "row_count": len(rows), "output_file": output_file})

    print(f"\n================= {label} ({len(rows)} rows) ============ \n{sql}\n")
    print(result.head(10).to_string(index=False))
    return result


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    sqllite_connection, cursor = getConnCursor()
    cursor.execute("DROP TABLE IF EXISTS books")
    cursor.execute("DROP TABLE IF EXISTS categories")

    #Task 4: normalized schema, two tables sharing a primary/foreign key.
    cursor.execute('''CREATE TABLE categories
    (category_id INTEGER PRIMARY KEY, category_name TEXT UNIQUE)''')

    cursor.execute('''CREATE TABLE books (book_id INTEGER PRIMARY KEY,
     title TEXT, price_gbp REAL, price_inr REAL, rating INTEGER,
     in_stock INTEGER, availability TEXT,
     category_id INTEGER REFERENCES categories(category_id))''')

    # make an request to the website
    response = requests.get("https://books.toscrape.com", timeout=30)
    response.raise_for_status()
    #print the response in the text format
    #print(response.text)


    soup = BeautifulSoup(response.text, 'html.parser')
    #get the components based on the navigation divs to get the categories component.
    #the nested ul skips the first "Books" link, which is the whole catalogue.
    #iterate only first 10 categories to the list of product for those categories.
    categories = soup.select("div.side_categories ul li ul li a")[:10]

    # Get list of category names by extracting text from the html tags of type anchor tag.
    category_data = {}
    all_books = []
    all_categories = []

#=================================================================
    #Task 1: Get the categories data
    for category in categories:
        # 1. Extract the text (e.g. "Travel")
        category_name = category.get_text(strip=True)
        
        # 2. Extract the href attribute (relative path)
        link = category.get("href")
        
        # 3. Combine with base URL to get full URL
        full_url = f"https://books.toscrape.com/{link}"

        # 4. Follow the "next" link so every page of the category is scraped.
        category_books = []
        while full_url:
            response = requests.get(full_url, timeout=30)
            response.raise_for_status()
            #the site serves utf-8 but does not declare it, so requests guesses latin-1.
            response.encoding = "utf-8"

            category_soup = BeautifulSoup(response.text, 'html.parser')
            category_books += category_soup.select("article.product_pod")

            next_link = category_soup.select_one("li.next a")
            full_url = urljoin(full_url, next_link["href"]) if next_link else None

        if len(category_books) > 0:
            books_data = []
            for book in category_books:
                # Read every field defensively: a missing tag or an unexpected
                # class list yields None instead of raising, so one malformed
                # product card cannot bring the whole pipeline down.
                try:
                    star_rating_classes = book.find("p", class_="star-rating")
                    rating_classes = star_rating_classes["class"] if star_rating_classes else []
                    raw_rating = rating_classes[1] if len(rating_classes) > 1 else None

                    price_tag = book.find("p", class_="price_color")
                    raw_price = price_tag.get_text(strip=True) if price_tag else None

                    title = book.find("h3").find("a")["title"]

                    availability = book.find("p", class_="instock availability")
                    #print(f"===== Availability of the product =====\n {availability}")
                    if availability:
                        availability = availability.get_text(strip=True)
                    else:
                        availability = "Not Available"
                except (AttributeError, KeyError, TypeError) as error:
                    # The title is the row's identity - without it the record is
                    # useless, so the card is dropped rather than imputed.
                    print(f"[drop] unreadable product card in '{category_name}': {error}")
                    continue

                print(availability)
                books_data.append({
                    "category": category_name,
                    "rating": raw_rating,
                    "price": raw_price,
                    "title": title,
                    "availability": availability
                })
            
            rating_map = {
                "One": 1,
                "Two": 2,
                "Three": 3,
                "Four": 4,
                "Five": 5
            }
#=================================================================
            #Task 2: Clean the scraped fields into proper types:

            # Pass 1: attempt to parse every row, marking any field that fails
            # as None so the failures can be counted and imputed afterwards.
            for book_data in books_data:
                raw_price = book_data.pop("price")
                try:
                    raw_price = raw_price.replace("Â£", "").replace("£", "").strip()
                    book_data["price_gbp"] = float(raw_price)
                except (AttributeError, ValueError):
                    print(f"[impute] unparseable price {raw_price!r} for '{book_data['title']}'")
                    book_data["price_gbp"] = None

                # rating_map returns None for anything outside One..Five
                book_data["rating"] = rating_map.get(book_data["rating"])
                if book_data["rating"] is None:
                    print(f"[impute] unparseable star rating for '{book_data['title']}'")

                # Match on a substring rather than the exact string so wording
                # like "In stock (19 available)" still resolves to True; anything
                # that mentions neither state is reported instead of silently
                # defaulting to False.
                availability = book_data["availability"].lower()
                if "in stock" in availability:
                    book_data["in_stock"] = True
                else:
                    if "out of stock" not in availability and "unavailable" not in availability:
                        print(f"[warn] unrecognised availability {book_data['availability']!r} "
                              f"for '{book_data['title']}' - treated as out of stock")
                    book_data["in_stock"] = False

            # Pass 2: median-impute the numeric fields that failed to parse.
            # Median rather than mean because a handful of extreme prices should
            # not drag the replacement value; imputing rather than dropping keeps
            # the row's other correct fields (title, category, stock) in the
            # dataset. A row is only dropped when the whole category failed to
            # parse and there is therefore no median to borrow.
            parsed_prices = [b["price_gbp"] for b in books_data if b["price_gbp"] is not None]
            parsed_ratings = [b["rating"] for b in books_data if b["rating"] is not None]
            median_price = median(parsed_prices) if parsed_prices else None
            median_rating = int(median(parsed_ratings)) if parsed_ratings else None

            cleaned_books = []
            for book_data in books_data:
                if book_data["price_gbp"] is None:
                    book_data["price_gbp"] = median_price
                if book_data["rating"] is None:
                    book_data["rating"] = median_rating

                if book_data["price_gbp"] is None or book_data["rating"] is None:
                    print(f"[drop] no median available to impute '{book_data['title']}'")
                    continue
                cleaned_books.append(book_data)

            books_data = cleaned_books
            print(books_data)
            category_data[category_name] = books_data
#=================================================================
        #Task 3: 
            # GBP to INR conversion
            # 1GBP = 105.50 INR
            for book in books_data:
                book["price_inr"] = book["price_gbp"] * 105.50
#=================================================================

        #Task 5: Using Python's sqlite3 (or pandas.DataFrame.to_sql),
        # insert your cleaned, converted data into this schema.
        cursor.execute("INSERT INTO categories (category_name) VALUES (?)", (category_name,))

        category_id = cursor.lastrowid
        all_categories.append({"category_id": category_id, "category_name": category_name})

        for book in books_data:
            #keep the same id in memory so pd.merge can join without touching sql.
            book["category_id"] = category_id
            cursor.execute("INSERT INTO books (title, price_gbp, price_inr, rating, in_stock, availability, category_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (book["title"], book["price_gbp"], book["price_inr"], book["rating"], book["in_stock"], book["availability"], category_id))

        all_books += books_data

    sqllite_connection.commit()
    sqllite_connection.close()
    print(f"\ntotal {len(all_books)} books across {len(all_categories)} categories")

    #the queries run once, against the fully loaded database.
    #each one is executed with sqlite3 and read back with pd.read_sql.
    run_query("distinct_ratings", "SELECT DISTINCT rating FROM books ORDER BY rating")
    run_query("select_where", "SELECT title, rating, in_stock FROM books WHERE rating > 4")
    run_query("order_by_price", "SELECT title, price_gbp FROM books ORDER BY price_gbp ASC")
    run_query("top_5_costliest", "SELECT title, price_gbp, price_inr FROM books ORDER BY price_gbp DESC LIMIT 5")
    run_query("price_between_20_and_40",
              "SELECT title, price_gbp, rating FROM books WHERE price_gbp BETWEEN 20 AND 40 AND rating IN (4, 5) ORDER BY price_gbp")
    join_sql = ("SELECT category_name, title, rating FROM books "
                "JOIN categories ON books.category_id = categories.category_id "
                "WHERE category_name = 'Travel' AND rating >= 4 ORDER BY rating DESC, title")
    read_sql_join = run_query("join_travel_top_rated", join_sql)

    #Task 6: reproduce the join with pd.merge on the in-memory data (no sql).
    books_df = pd.DataFrame(all_books)
    categories_df = pd.DataFrame(all_categories)
    merged_books_cat = pd.merge(books_df, categories_df, on="category_id", how="inner")
    merge_join = (merged_books_cat[(merged_books_cat["category_name"] == "Travel") & (merged_books_cat["rating"] >= 4)]
                  [["category_name", "title", "rating"]]
                  .sort_values(["rating", "title"], ascending=[False, True])
                  .reset_index(drop=True))

    side_by_side = pd.concat({"pd.read_sql": read_sql_join, "pd.merge": merge_join}, axis=1)
    print("\n================= pd.read_sql vs pd.merge ============ \n", side_by_side.to_string())
    print("\nidentical:", read_sql_join.equals(merge_join))

    side_by_side.to_csv(OUTPUT_DIR / "read_sql_vs_merge.csv", index=False)
    pd.DataFrame(query_log).to_csv(OUTPUT_DIR / "queries.csv", index=False)
    print(f"query output saved to {OUTPUT_DIR.name}/")


if __name__ == "__main__":
    main()