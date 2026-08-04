# first import the required libraries
# pip3 install requests BeautifulSoup4
# pyrefly: ignore [missing-import]
import requests
from bs4 import BeautifulSoup
import sqlite3
import pandas as pd
from statistics import median

#run this script from inside the data_pipeline folder.
DB_PATH = "books.db"
OUTPUT_FILE = "query_outputs.md"

#every query string and its output, written to query_outputs.md at the end.
query_log = []


def getConnCursor():
    """common place that opens the sqlite connection and returns it with its cursor."""
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    return connection, cursor


def main():
    sqllite_connection, cursor = getConnCursor()
    cursor.execute("DROP TABLE IF EXISTS books")
    cursor.execute("DROP TABLE IF EXISTS categories")

    # make an request to the website
    response = requests.get("https://books.toscrape.com", timeout=30)
    response.raise_for_status()
    #print the response in the text format
    #print(response.text)


    soup = BeautifulSoup(response.text, 'html.parser')
    #get the components based on the navigation divs to get the categories component.
    #iterate only first 10 categories to the list of product for those categories.
    categories = soup.select("div.side_categories ul li ul li a")[1:11]

    # Get list of category names by extracting text from the html tags of type anchor tag.
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

        # 4. Get the listing page of the category and pick every product on it.
        response = requests.get(full_url, timeout=30)
        response.raise_for_status()
        #the site serves utf-8 but does not declare it, so requests guesses latin-1.
        response.encoding = "utf-8"

        category_soup = BeautifulSoup(response.text, 'html.parser')
        category_books = category_soup.select("article.product_pod")

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

                #print(availability)
                books_data.append({
                    "category": category_name,
                    "rating": raw_rating,
                    "price": raw_price,
                    "title": title,
                    "availability": availability
                })
            
            
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
                rating_map = {
                    "One": 1,
                    "Two": 2,
                    "Three": 3,
                    "Four": 4,
                    "Five": 5
                }
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

            #get the medians for rating and price since they are numeric data types at this moment.
            # Step 1: collect the values that did parse, they are what the median is built from.
            parsed_prices = []
            parsed_ratings = []
            for book_data in books_data:
                if book_data["price_gbp"] is not None:
                    parsed_prices.append(book_data["price_gbp"])

                if book_data["rating"] is not None:
                    parsed_ratings.append(book_data["rating"])

            # Step 2: work out the median of each field, None when nothing parsed.
            median_price = None
            if len(parsed_prices) > 0:
                median_price = median(parsed_prices)

            median_rating = None
            if len(parsed_ratings) > 0:
                #cast to int so the column stays a 1-5 integer instead of becoming 3.5
                median_rating = int(median(parsed_ratings))

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

#=================================================================
        #Task 3: 
            # GBP to INR conversion
            # 1GBP = 105.50 INR
            for book in books_data:
                book["price_inr"] = book["price_gbp"] * 105.50
#=================================================================

        #Task 4: Design a normalized SQLite schema with at least two tables
        # sharing a primary/foreign key relationship. IF NOT EXISTS keeps this
        # a no-op after the first category, the tables are dropped once in main.
        cursor.execute('''CREATE TABLE IF NOT EXISTS categories
        (category_id INTEGER PRIMARY KEY, category_name TEXT UNIQUE)''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS books (book_id INTEGER PRIMARY KEY,
         title TEXT, price_gbp REAL, price_inr REAL, rating INTEGER,
         in_stock INTEGER, availability TEXT,
         category_id INTEGER REFERENCES categories(category_id))''')
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

    #Task 5 continued: the queries run once, against the fully loaded database.
    sqllite_connection, cursor = getConnCursor()

    # 1. Get all categories inserted into the system
    categories_sql = "SELECT * FROM categories LIMIT 5"
    cursor.execute(categories_sql)
    all_categories_rows = cursor.fetchall()
    print("\n================= All the categories inserted into the system ============ \n", all_categories_rows)
    query_log.append(("all_categories", categories_sql,
                      pd.DataFrame(all_categories_rows, columns=[column[0] for column in cursor.description]).to_string(index=False)))

    # 2. Get all books where rating is greater than 4.
    rating_sql = "SELECT * FROM books WHERE rating > 4 LIMIT 5"
    cursor.execute(rating_sql)
    books_rating_greater_than_4 = cursor.fetchall()
    print("\n================= Books whose rating is greater than 4 ============ \n", books_rating_greater_than_4)
    query_log.append(("books_rating_greater_than_4", rating_sql,
                      pd.DataFrame(books_rating_greater_than_4, columns=[column[0] for column in cursor.description]).to_string(index=False)))

    # 3. Get all books in ascending order of price.
    order_by_sql = "SELECT * FROM books ORDER BY price_gbp ASC LIMIT 5"
    cursor.execute(order_by_sql)
    books_ascending_price = cursor.fetchall()
    print("\n================= All books in ascending order of price ============ \n", books_ascending_price)
    query_log.append(("books_ascending_price", order_by_sql,
                      pd.DataFrame(books_ascending_price, columns=[column[0] for column in cursor.description]).to_string(index=False)))

    # 4. Get all books where the price is between 20 and 40.
    between_sql = "SELECT * FROM books WHERE price_gbp BETWEEN 20 AND 40 LIMIT 5"
    cursor.execute(between_sql)
    books_price_range = cursor.fetchall()
    print("\n================= All books whose price is between 20 and 40 ============ \n", books_price_range)
    query_log.append(("books_price_between_20_and_40", between_sql,
                      pd.DataFrame(books_price_range, columns=[column[0] for column in cursor.description]).to_string(index=False)))

    # 5. Get all books limit 5
    limit_sql = "SELECT * FROM books LIMIT 5"
    cursor.execute(limit_sql)
    books_limit_5 = cursor.fetchall()
    print("\n================= All books limit 5 ============ \n", books_limit_5)
    query_log.append(("books_limit_5", limit_sql,
                      pd.DataFrame(books_limit_5, columns=[column[0] for column in cursor.description]).to_string(index=False)))

    # 6. Get all books distinct title and whose category is "Mystery" with join
    join_sql = ("SELECT DISTINCT title, category_name FROM books "
                "JOIN categories ON books.category_id = categories.category_id "
                "WHERE categories.category_name = 'Mystery' LIMIT 5")
    cursor.execute(join_sql)
    books_distinct_title_mystery = cursor.fetchall()
    print("\n================= All distinct book titles in the Mystery category ============ \n", books_distinct_title_mystery)
    query_log.append(("join_distinct_mystery_titles", join_sql,
                      pd.DataFrame(books_distinct_title_mystery, columns=[column[0] for column in cursor.description]).to_string(index=False)))

    #Task 6: read the query results back into pandas DataFrames.
    read_sql_books_rating_gt_4 = pd.read_sql(rating_sql, con=sqllite_connection)
    print("\n================= Read Books with rating greater than 4 ============ \n", read_sql_books_rating_gt_4)

    read_sql_books_limit_5 = pd.read_sql(limit_sql, con=sqllite_connection)
    print("\n================= Read Books limit 5 ============ \n", read_sql_books_limit_5)

    read_sql_join = pd.read_sql(join_sql, con=sqllite_connection)
    print("\n================= Read distinct Mystery titles with join ============ \n", read_sql_join)
    sqllite_connection.close()

    #reproduce the same join with pd.merge on the in-memory data, no sql involved.
    books_df = pd.DataFrame(all_books)
    categories_df = pd.DataFrame(all_categories)
    merged_books_cat = pd.merge(books_df, categories_df, on="category_id", how="inner")
    merge_join = (merged_books_cat[merged_books_cat["category_name"] == "Mystery"]
                  [["title", "category_name"]]
                  .drop_duplicates()
                  #head(5) mirrors the LIMIT 5 in the sql above, otherwise the two differ.
                  .head(5)
                  .reset_index(drop=True))

    #show both results next to each other and check they are the same.
    side_by_side = pd.concat({"pd.read_sql": read_sql_join, "pd.merge": merge_join}, axis=1)
    is_identical = read_sql_join.equals(merge_join)
    print("\n================= pd.read_sql vs pd.merge ============ \n", side_by_side.to_string())
    print("\nidentical:", is_identical)
    query_log.append(("pd.read_sql vs pd.merge", join_sql,
                      f"{side_by_side.to_string()}\n\nequals -> {is_identical}"))

    #save every query string with its output.
    with open(OUTPUT_FILE, "w") as output:
        output.write("# SQL Queries and Their Output\n")
        for number, (label, sql, rows) in enumerate(query_log, start=1):
            output.write(f"\n## {number}. {label}\n"
                         f"```sql\n{sql}\n```\n"
                         f"```\n{rows}\n```\n")
    print(f"query output saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()