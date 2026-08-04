# SQL Queries and Their Output

## 1. all_categories
```sql
SELECT * FROM categories LIMIT 5
```
```
 category_id      category_name
           1            Mystery
           2 Historical Fiction
           3     Sequential Art
           4           Classics
           5         Philosophy
```

## 2. books_rating_greater_than_4
```sql
SELECT * FROM books WHERE rating > 4 LIMIT 5
```
```
 book_id                                                                    title  price_gbp  price_inr  rating  in_stock availability  category_id
       9                                   A Time of Torment (Charlie Parker #14)      48.35   5100.925       5         1     In stock            1
      18        What Happened on Beale Street (Secrets of the South Mysteries #2)      25.37   2676.535       5         1     In stock            1
      19 The Bachelor Girl's Guide to Murder (Herringford and Watts Mysteries #1)      52.30   5517.650       5         1     In stock            1
      23                                  A Flight of Arrows (The Pathfinders #2)      55.53   5858.415       5         1     In stock            2
      25                                                             Mrs. Houdini      30.25   3191.375       5         1     In stock            2
```

## 3. books_ascending_price
```sql
SELECT * FROM books ORDER BY price_gbp ASC LIMIT 5
```
```
 book_id                                    title  price_gbp  price_inr  rating  in_stock availability  category_id
      49                                 Patience      10.16   1071.880       3         1     In stock            3
     146                I Am Pilgrim (Pilgrim #1)      10.60   1118.300       4         1     In stock            8
       8     Tastes Like Fear (DI Marnie Rome #3)      10.69   1127.795       1         1     In stock            1
      14               Hide Away (Eve Duncan #20)      11.84   1249.120       1         1     In stock            1
     109 Dark Lover (Black Dagger Brotherhood #1)      12.87   1357.785       1         1     In stock            6
```

## 4. books_price_between_20_and_40
```sql
SELECT * FROM books WHERE price_gbp BETWEEN 20 AND 40 LIMIT 5
```
```
 book_id                                                             title  price_gbp  price_inr  rating  in_stock availability  category_id
      11                                  Poisonous (Max Revere Novels #3)      26.80   2827.400       3         1     In stock            1
      13                                                       Most Wanted      35.28   3722.040       3         1     In stock            1
      16                                                         The Widow      27.26   2875.930       2         1     In stock            1
      18 What Happened on Beale Street (Secrets of the South Mysteries #2)      25.37   2676.535       5         1     In stock            1
      20                  Delivering the Truth (Quaker Midwife Mystery #1)      20.89   2203.895       4         1     In stock            1
```

## 5. books_limit_5
```sql
SELECT * FROM books LIMIT 5
```
```
 book_id                                           title  price_gbp  price_inr  rating  in_stock availability  category_id
       1                                   Sharp Objects      47.82   5045.010       4         1     In stock            1
       2                            In a Dark, Dark Wood      19.63   2070.965       1         1     In stock            1
       3                             The Past Never Ends      56.50   5960.750       4         1     In stock            1
       4                                A Murder in Time      16.64   1755.520       1         1     In stock            1
       5 The Murder of Roger Ackroyd (Hercule Poirot #4)      44.10   4652.550       4         1     In stock            1
```

## 6. join_distinct_mystery_titles
```sql
SELECT DISTINCT title, category_name FROM books JOIN categories ON books.category_id = categories.category_id WHERE categories.category_name = 'Mystery' LIMIT 5
```
```
                                          title category_name
                                  Sharp Objects       Mystery
                           In a Dark, Dark Wood       Mystery
                            The Past Never Ends       Mystery
                               A Murder in Time       Mystery
The Murder of Roger Ackroyd (Hercule Poirot #4)       Mystery
```

## 7. pd.read_sql vs pd.merge
```sql
SELECT DISTINCT title, category_name FROM books JOIN categories ON books.category_id = categories.category_id WHERE categories.category_name = 'Mystery' LIMIT 5
```
```
                                       pd.read_sql                                                       pd.merge              
                                             title category_name                                            title category_name
0                                    Sharp Objects       Mystery                                    Sharp Objects       Mystery
1                             In a Dark, Dark Wood       Mystery                             In a Dark, Dark Wood       Mystery
2                              The Past Never Ends       Mystery                              The Past Never Ends       Mystery
3                                 A Murder in Time       Mystery                                 A Murder in Time       Mystery
4  The Murder of Roger Ackroyd (Hercule Poirot #4)       Mystery  The Murder of Roger Ackroyd (Hercule Poirot #4)       Mystery

equals -> True
```
