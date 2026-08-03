# first import the required libraries
# pip3 install requests BeautifulSoup4
# pyrefly: ignore [missing-import]
import requests
from bs4 import BeautifulSoup
import json
import sqlite3
import pandas as pd

sqllite_connection = sqlite3.connect("books.db")
#create the cursor used to execute the sql commands.
cursor = sqllite_connection.cursor()
cursor.execute("DROP TABLE IF EXISTS books")
cursor.execute("DROP TABLE IF EXISTS categories")


def main():
    # make an request to the website
    response = requests.get("https://books.toscrape.com")
    #print the response in the text format
    #print(response.text)


    soup = BeautifulSoup(response.text, 'html.parser')
    #get the components based on the navigation divs to get the categories component.
    #iterate only first 10 categories to the list of product for those categories.
    categories = soup.select("div.side_categories ul li a")[:10]

    # Get list of category names by extracting text from the html tags of type anchor tag. 
    category_data = {}
    
#=================================================================
    #Task 1: Get the categories data
    for category in categories:
        # 1. Extract the text (e.g. "Travel")
        category_name = category.get_text(strip=True)
        
        # 2. Extract the href attribute (relative path)
        link = category.get("href")
        
        # 3. Combine with base URL to get full URL
        full_url = f"https://books.toscrape.com/{link}"

        response = requests.get(full_url)

        category_soup = BeautifulSoup(response.text, 'html.parser')
        category_books = category_soup.select("article.product_pod")
        
        if len(category_books) > 0:
            books_data = []
            for book in category_books:
                star_rating_classes = book.find("p", class_="star-rating")
                rating = star_rating_classes["class"]
                price_tag = book.find("p", class_="price_color")
                raw_price = price_tag.get_text(strip=True)

                title = book.find("h3").find("a")["title"]
                availability = book.find("p", class_="instock availability")
                #print(f"===== Availability of the product =====\n {availability}")
                if availability:
                    availability = availability.get_text(strip=True)
                else:
                    availability = "Not Available"
                print(availability)
                books_data.append({
                    "category": category_name,
                    "rating": rating[1],
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

            for book_data in books_data:
                book_data["price"] = book_data["price"].replace("Â£", "").replace("£", "").strip()
                book_data["price"] = float(book_data["price"])
                book_data["rating"] = rating_map.get(book_data["rating"], 0)
                if book_data["availability"] == "In stock":
                    book_data["in_stock"] = True
                else:
                    book_data["in_stock"] = False
                del book_data["availability"]

                if book_data["price"]:
                    book_data["price_gbp"] = book_data["price"]
                    del book_data["price"]

            print(books_data)
            category_data[category_name] = books_data
#=================================================================
        #Task 3: 
            # GBP to INR conversion
            # 1GBP = 105.50 INR
            for book in books_data:
                book["price_inr"] = book["price_gbp"] * 105.50
#=================================================================

        #Task 4: Design a normalized SQLite schema with at
        #  least two tables sharing a primary/foreign key 
        # relationship, for example:
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS categories 
        (category_id INTEGER PRIMARY KEY, category_name TEXT UNIQUE)''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS books (book_id INTEGER PRIMARY KEY,
         title TEXT, price_gbp REAL, price_inr REAL, rating INTEGER, 
         in_stock INTEGER, category_id INTEGER REFERENCES categories(category_id))''')
        
        #Task 5: Using Python's sqlite3 (or pandas.DataFrame.to_sql), 
        # insert your cleaned, converted data into this schema. 
        cursor.execute("INSERT INTO categories (category_name) VALUES (?)", (category_name,))

        category_id = cursor.lastrowid
        for book in books_data:
            cursor.execute("INSERT INTO books (title, price_gbp, price_inr, rating, in_stock, category_id) VALUES (?, ?, ?, ?, ?, ?)", 
            (book["title"], book["price_gbp"], book["price_inr"], book["rating"], book["in_stock"], category_id))

        #we need to write 5 queries to retrive the data from the database.
        # 1. Get all categories inserted into the system
        # each time we are inserting one category 
        # so products belongs to one category will be inserted and queried.
        cursor.execute("SELECT * FROM categories")
        categories = cursor.fetchall()
        print("\n================= All the categories inserted into the system so far ==================\n", categories)
        # 2. Get all books where rating is greater than 4.
        cursor.execute("SELECT * from books where rating > 4")
        books_rating_greater_than_4 = cursor.fetchall()
        print("\n================= Books whose rating greater that 4 ============ \n" , books_rating_greater_than_4)
        # 3. Get all books in ascending order of price.
        cursor.execute("SELECT * FROM BOOKS ORDER BY price_gbp ASC")
        books_ascending_price = cursor.fetchall()
        print("\n================= All books in ascending order of price ============ \n" , books_ascending_price)
        # 4. Get all books where the price is between 10 and 20.
        cursor.execute("SELECT * FROM BOOKS where price_gbp between 20 and 40")
        books_price_range = cursor.fetchall()
        print("\n================= All books whose price is between 20 and 40 ============ \n" , books_price_range)
        # 5. Get all books limit 5
        cursor.execute("SELECT * FROM BOOKS LIMIT 5")
        books_limit_5 = cursor.fetchall()
        print("\n================= All books limit 5 ============ \n" , books_limit_5)
        # 6. Get All books distinct title and whose category is "Travel" with join
        cursor.execute("SELECT DISTINCT title, category_name FROM books JOIN categories ON books.category_id = categories.category_id WHERE categories.category_name = 'Travel'")
        books_distinct_title_fantacy = cursor.fetchall()
        print("\n================= All books distinct title and whose category is Travel ============ \n" , books_distinct_title_fantacy)

        #Task 6: Read back at least two of the above query results into pandas DataFrames using pd.read_sql(...), 
        # and separately reproduce the join-query's result using pd.merge(...) 
        # directly on your in-memory DataFrames (no SQL) 

        read_sql_categories = pd.read_sql("SELECT * FROM categories", con=sqllite_connection)
        print("\n================= Read Categories ============ \n" , read_sql_categories)

        read_sql_books = pd.read_sql("SELECT * FROM books", con=sqllite_connection)
        print("\n================= Read Books ============ \n" , read_sql_books)

        # Read books with rating greater than 4
        read_sql_books_rating_gt_4 = pd.read_sql("SELECT * FROM books WHERE rating > 4", con=sqllite_connection)
        print("\n================= Read Books with rating greater than 4 ============ \n" , read_sql_books_rating_gt_4)

        # Read books in ascending order of price
        read_sql_books_asc_price = pd.read_sql("SELECT * FROM BOOKS ORDER BY price_gbp ASC", con=sqllite_connection)
        print("\n================= Read Books in ascending order of price ============ \n" , read_sql_books_asc_price)

        # Read books where the price is between 10 and 20
        read_sql_books_price_range = pd.read_sql("SELECT * FROM BOOKS where price_gbp between 20 and 40", con=sqllite_connection)
        print("\n================= Read Books price between 20 and 40 ============ \n" , read_sql_books_price_range)

        # Read books limit 5
        read_sql_books_limit_5 = pd.read_sql("SELECT * FROM BOOKS LIMIT 5", con=sqllite_connection)
        print("\n================= Read Books limit 5 ============ \n" , read_sql_books_limit_5)

        # Read all books distinct title and whose category is Travel with join
        read_sql_books_distinct_title_category = pd.read_sql('''SELECT DISTINCT title, category_name FROM books JOIN categories 
        ON books.category_id = categories.category_id WHERE categories.category_name = "Travel"''', con=sqllite_connection)
        print("\n================= Read Books distinct title and whose category is Travel ============ \n" , read_sql_books_distinct_title_category)

        # Reproduce the SQL JOIN in pandas: Merge books and categories on "category_id"
        merged_books_cat = pd.merge(read_sql_books, read_sql_categories, on="category_id", how="inner")

        # Filter for category "Travel" and select distinct title & category_name
        travel_books_df = merged_books_cat[merged_books_cat["category_name"] == "Travel"][["title", "category_name"]].drop_duplicates()
        print("\n================= Pandas Merge Result (Travel Books) ============ \n", travel_books_df)


    sqllite_connection.commit()
    sqllite_connection.close()

    #print(json.dumps(category_data, indent=4))


if __name__ == "__main__":
    main()