# Module 2 - Analytics Pipeline (Titanic Survival Analysis)

This module covers the full data analysis and machine learning pipeline on the
Titanic dataset. The goal is to understand what kind of passenger was more
likely to survive, and then to build models that predict survival.

The dataset describes 891 passengers who were on the Titanic in 1912. It is
loaded from seaborn exactly once, and every step after that works from that same
data.

The work is split across two notebooks. The first handles all the exploration
and cleaning, the second handles all the machine learning.

---

## Note - The Markdown Used in This File

Before the sections begin, a short note on how this document is written. Only two
pieces of markdown formatting are used, code blocks and tables.

Code blocks are written with the backtick character, which is the key above Tab
and to the left of the number 1. It is not the apostrophe or single quote.

Three backticks open the block, the language name goes right after them with no
space, and three backticks on their own line close it.

````
```python
df["age"] = df["age"].fillna(df["age"].median())
```
````

That renders as this.

```python
df["age"] = df["age"].fillna(df["age"].median())
```

| Rule | Detail |
| --- | --- |
| Opening line | Three backticks, then the language name, no space between them |
| Language names used in this README | python, bash |
| Closing line | Three backticks alone, nothing after them |
| If the language is left out | It still renders as code, only without colour highlighting |
| Spacing | Leave a blank line before the opening and after the closing line |

A table is made of pipe characters. The second row, the one made of dashes, is
required. It is what tells markdown these lines are a table and not plain text.

```
| Model | Accuracy |
| --- | --- |
| Decision Tree | 0.816 |
```

That renders as this.

| Model | Accuracy |
| --- | --- |
| Decision Tree | 0.816 |

| Rule | Detail |
| --- | --- |
| First row | The column headings |
| Second row | One set of three dashes per column, mandatory |
| Third row onward | The data rows |
| Column count | Every row needs the same number of pipe separators |
| Spacing | The pipes do not have to line up in the source file |

---

## Section 1 - Files in this Folder

| File | What it is |
| --- | --- |
| 01_eda.ipynb | Loads the dataset, profiles it, cleans it, saves titanic.csv, and produces the whole EDA story. |
| 02_modeling.ipynb | Reads that same titanic.csv and runs the modeling, tuning, regression side task and final save. |
| titanic.csv | The offline copy of the dataset, written straight after loading so grading works without internet. |
| titanic_survival_pipeline.pkl | The saved trained pipeline, preprocessing and classifier together in one object. |
| charts/ | The 14 saved chart images, written by the notebooks themselves. |
| README.md | This file. |

Every chart is saved to disk as a PNG by the cell that draws it, using
plt.savefig just before plt.show, so the images are regenerated whenever the
notebooks are rerun rather than being exported by hand.

| File in charts/ | Chart | Notebook |
| --- | --- | --- |
| 01_age_histogram.png | Distribution of age | 01_eda |
| 02_age_boxplot.png | Box plot of age, showing the IQR outliers | 01_eda |
| 03_fare_histogram.png | Distribution of fare | 01_eda |
| 04_fare_boxplot.png | Box plot of fare | 01_eda |
| 05_correlation_matrix.png | The 6 by 6 correlation matrix | 01_eda |
| 06_survival_rate_by_sex.png | Data story chart 1 | 01_eda |
| 07_survival_rate_by_class.png | Data story chart 2 | 01_eda |
| 08_age_distribution_by_survival.png | Data story chart 3 | 01_eda |
| 09_age_vs_fare_by_survival.png | Data story chart 4 | 01_eda |
| 10_correlation_heatmap.png | Correlation heatmap | 01_eda |
| 11_survival_rate_by_sex_and_class.png | Data story chart 5 | 01_eda |
| 12_decision_tree.png | The decision tree drawn with plot_tree | 02_modeling |
| 13_roc_curves.png | ROC curves for all three classifiers | 02_modeling |
| 14_residual_plot.png | Residual plot for the fare regression | 02_modeling |

Install the libraries and run the notebooks in order.

```bash
pip install pandas seaborn matplotlib scikit-learn imbalanced-learn joblib
```

Run 01_eda.ipynb first, then 02_modeling.ipynb.

The network is used exactly once, in the first cell of 01_eda.ipynb. Every later
step, including everything in 02_modeling.ipynb, works from the titanic.csv that
first load produced. There is no second sns.load_dataset call anywhere in the
module.

---

## Section 2 - Loading and Profiling the Dataset

The dataset is loaded with seaborn's built in loader and immediately saved to
disk.

```python
df = sns.load_dataset("titanic")
df.to_csv("titanic.csv", index=False)
```

Saving straight after loading is what makes the rest of the module reproducible
and offline. Anyone grading it can rerun everything from the committed CSV with
no internet connection.

Three profiling commands are used.

| Command | What it shows |
| --- | --- |
| df.shape | 891 rows and 15 columns |
| df.info() | Every column name, its data type, and how many non null values it has |
| df.describe() | Count, mean, standard deviation, minimum, quartiles and maximum for the numeric columns |

The 15 columns break down as follows.

| Column | Type | Meaning |
| --- | --- | --- |
| survived | int | 0 did not survive, 1 survived. This is the target. |
| pclass | int | Ticket class, 1, 2 or 3 |
| sex | text | male or female |
| age | float | Age in years, has missing values |
| sibsp | int | Number of siblings and spouses aboard |
| parch | int | Number of parents and children aboard |
| fare | float | Ticket price paid |
| embarked | text | Port code, S, C or Q, has missing values |
| class | category | The word form of pclass, First, Second, Third |
| who | text | man, woman or child |
| adult_male | bool | True for adult men |
| deck | category | Cabin deck letter, mostly missing |
| embark_town | text | The full port name, has missing values |
| alive | text | yes or no, the word form of survived |
| alone | bool | True when sibsp plus parch is zero |

Several columns are duplicates of each other in a different form. class repeats
pclass, alive repeats survived, and embark_town repeats embarked. This matters
later when choosing model features, because feeding both alive and survived to a
model would hand it the answer directly.

The fare column was also sorted from highest to lowest to see the spread. The
three most expensive tickets were all 512.33, while the median fare is 14.45.
That gap is the first sign of the skew examined in Section 4.

---

## Section 3 - Handling Missing Values

Four columns have missing values. The exact percentages, measured on the raw 891
row dataset, are below.

| Column | Missing percent | Missing rows |
| --- | --- | --- |
| age | 19.87 | 177 |
| deck | 77.22 | 688 |
| embarked | 0.22 | 2 |
| embark_town | 0.22 | 2 |

A fixed threshold rule decides what happens to each one.

| Missing percent | Rule |
| --- | --- |
| Under 5 percent | Drop the affected rows |
| Between 5 and 30 percent | Impute, meaning fill in a sensible value |
| Above 30 percent | Drop the column, or treat missing as its own category |

Applying that rule gives the following.

| Column | Percent | Band | Action taken | Why this is the right call |
| --- | --- | --- | --- | --- |
| embarked | 0.22 | Under 5 | Dropped the 2 affected rows | Losing 2 rows out of 891 costs nothing, and inventing a port of embarkation would be making up a fact about a real person. |
| embark_town | 0.22 | Under 5 | The same 2 rows | It is the text form of embarked, so the identical 2 rows are affected. Nothing extra is lost. |
| age | 19.87 | 5 to 30 | Filled with the median, 28.0 | Sits squarely in the impute band. 177 rows is too many to throw away, since that would be a fifth of the dataset. |
| deck | 77.22 | Above 30 | The whole column dropped | Explained below. |

Age is filled with the median rather than the mean for a specific reason. Age is
right skewed, with a tail of older passengers pulling the average up. The mean
age is 29.70 while the median is 28.00. The median is the more typical passenger
and is not moved by a handful of very old people, so it is the safer filler.

```python
df["age"] = df["age"].fillna(df["age"].median())
```

Deck deserves more explanation because two options were considered and both were
rejected before dropping the column.

| Option | What would happen | Verdict |
| --- | --- | --- |
| Impute the missing decks | 77 percent of the column would be invented. Whatever value was chosen would become the majority of the column and would create a pattern that does not exist in the real data. | Rejected |
| Drop the rows with a missing deck | 688 of 891 rows would be removed, leaving only 203. Nearly 80 percent of the entire dataset would be lost to save one column. | Rejected |
| Encode missing as its own category | This was considered seriously. The problem is what that category would actually mean. It would mean "no cabin recorded", which in practice means "travelled in third class", and pclass already carries that information. | Rejected as redundant |
| Drop the column | 14 columns remain, every row is kept, and nothing is invented. | Chosen |

After cleaning, the dataset is 889 rows and 14 columns. Two rows were lost to
embarked and one column to deck.

---

## Section 4 - Univariate Analysis

Univariate means looking at one column at a time. A histogram and a box plot were
produced for both age and fare.

The age histogram is roughly bell shaped with a peak between 20 and 40, plus a
visible bump at the very low end for infants and young children. The fare
histogram is completely different in shape, with most passengers bunched at the
cheap end and a long thin tail stretching right.

Outliers were counted with the IQR rule. IQR means interquartile range, the
distance between the 25th percentile (Q1) and the 75th percentile (Q3). Anything
below Q1 minus 1.5 times the IQR, or above Q3 plus 1.5 times the IQR, counts as
an outlier.

| Column and stage | Q1 | Q3 | IQR | Lower bound | Upper bound | Outliers |
| --- | --- | --- | --- | --- | --- | --- |
| age, before imputation | 20.125 | 38.0 | 17.875 | -6.688 | 64.813 | 11 |
| age, after imputation | 22.0 | 35.0 | 13.0 | 2.5 | 54.5 | 65 |
| fare | 7.896 | 31.0 | 23.104 | -26.761 | 65.656 | 114 |

The age row is reported twice on purpose, and the difference between 11 and 65 is
worth understanding because it is easy to misread.

Imputing 177 missing ages all at 28.0 dumps a large block of identical values at
the exact centre of the distribution. That squeezes the quartiles inward, so the
IQR shrinks from 17.875 to 13.0 and the upper bound falls from 64.81 to 54.50.
Ages that were comfortably inside the whiskers before, such as a 60 year old
passenger, now sit outside them.

So the extra 54 outliers are not newly discovered extreme ages. They are ordinary
ages that were reclassified by the imputation itself. This is a real side effect
of median imputation and it is why the two counts are both reported rather than
only the final one.

Fare has no missing values, so nothing similar happens to it. Its 114 outliers on
the cleaned frame are genuine, mostly first class passengers who paid very large
amounts.

The lower bounds are negative for both columns, at -6.69 for raw age and -26.76
for fare. Since neither age nor a ticket price can be below zero, this means
there are no low outliers at all in either column. Every outlier counted is a
high one.

Fare skewness was measured with three statistics.

| Statistic | Value |
| --- | --- |
| Mean | 32.20 |
| Median | 14.45 |
| Mode | 8.05 |

The ordering is mode 8.05, then median 14.45, then mean 32.20. When mode is less
than median which is less than mean, the distribution is right skewed, also
called positively skewed.

The reason is visible in the raw data. A small group of wealthy passengers paid
up to 512.33 for a ticket. Those few values pull the mean up to more than double
the median, while most passengers actually paid single digit fares. The median is
therefore the more honest summary of a typical fare.

Note on the exact figure. 32.20 is the mean over all 891 raw rows, which is what
the notebook prints. On the 889 row cleaned frame the mean is 32.10. The
difference is the two dropped embarked rows and it does not change the skew
conclusion in any way.

---

## Section 5 - Bivariate Analysis

Bivariate means comparing two columns to find a pattern. Survival rates were
computed with boolean masking.

Part A, survival by sex.

| Sex | Passengers | Survivors | Survival rate |
| --- | --- | --- | --- |
| Female | 314 | 233 | 74.20 percent |
| Male | 577 | 109 | 18.89 percent |

Women survived at nearly four times the rate of men. This is the single largest
gap anywhere in the data and it strongly suggests the evacuation followed a women
and children first rule.

Part B, survival by passenger class.

| Class | Passengers | Survivors | Survival rate |
| --- | --- | --- | --- |
| First | 216 | 136 | 62.96 percent |
| Second | 184 | 87 | 47.28 percent |
| Third | 491 | 119 | 24.24 percent |

Survival falls steadily as the class number rises. First class cabins were on the
upper decks, closer to the lifeboats, and those passengers had priority during
the evacuation.

A note on reading these numbers carefully. The notebook also prints a second set
of figures for class, 39.77 for first, 25.44 for second and 34.80 for third.
Those are a different quantity. They are each class's share of all 342 survivors,
and they add up to 100 percent. They are not survival rates and they must not be
read as such, because third class looks better than second in that set purely
because third class was much larger. The survival rates in the table above are
the correct comparison.

Part C, survival by sex and class together.

| Sex | Class | Passengers | Survivors | Survival rate |
| --- | --- | --- | --- | --- |
| Female | 1 | 94 | 91 | 96.81 percent |
| Female | 2 | 76 | 70 | 92.11 percent |
| Female | 3 | 144 | 72 | 50.00 percent |
| Male | 1 | 122 | 45 | 36.89 percent |
| Male | 2 | 108 | 17 | 15.74 percent |
| Male | 3 | 347 | 47 | 13.54 percent |

The most striking line in this table is the comparison between female third class
at 50.00 percent and male first class at 36.89 percent. A woman in the cheapest
cabins was more likely to survive than a man in the most expensive ones. Sex
mattered more than class, though both mattered.

A correlation matrix was then computed on exactly six columns, survived, pclass,
age, sibsp, parch and fare, and drawn as a heatmap.

The derived flags adult_male and alone were deliberately excluded. adult_male is
computed from sex and age, and alone is computed from whether sibsp plus parch is
zero. They are not independent measurements, so including them would report the
same information twice and inflate the apparent number of relationships.

The two strongest relationships, ranked by absolute value off the diagonal.

| Rank | Pair | Coefficient | What it means |
| --- | --- | --- | --- |
| 1 | pclass and fare | -0.549 | Strong and negative. First class tickets were the most expensive and third class the cheapest, so as the class number rises the fare falls. The two columns largely encode the same underlying thing, a passenger's wealth. |
| 2 | sibsp and parch | +0.415 | Positive. Passengers travelling with a sibling or spouse also tended to have parents or children aboard. Both are measuring family group size, which is exactly why the derived alone flag is redundant with them. |

---

## Section 6 - Multivariate Data Story

Five charts were produced to tell one connected story.

| Chart | Type | What it shows |
| --- | --- | --- |
| 1 | Bar chart | Survival rate by sex. Female far above male. The single strongest factor. |
| 2 | Bar chart | Survival rate by class. Falls steadily from first to third. |
| 3 | Box plot | Age distribution split by survival. The two boxes overlap heavily. |
| 4 | Scatter plot | Age on the x axis, fare on the y axis, coloured by survival. |
| 5 | Grouped bar chart | Survival rate by sex with class as the hue, the two factors combined. |

Chart 3 is the one that says the least, and that is itself the finding. Survivors
and non survivors have a very similar spread of ages, so age on its own is a weak
predictor. The median age of survivors is slightly lower, which fits children
having been given some priority, but the effect is small next to sex and class.

Chart 4 shows the pattern that a table cannot. The dense cluster of non survivors
sits along the bottom of the plot, at low fares, across every age group. The
sparse points high up the fare axis are almost all survivors. Since fare tracks
class, this is the class effect made visible.

Chart 5 combines the two strongest factors and is the clearest single picture in
the module. Women outrank men in every class, and the female third class bar
still stands above the male first class bar.

The conclusion from all five charts together is that survival was driven mainly
by sex and secondarily by class. Women were prioritised during the evacuation.
First class passengers had physical and social advantages in reaching the
lifeboats. Fare correlates with survival because fare reflects class. Age had a
smaller role, limited mostly to young children.

---

## Section 7 - Standardization as an EDA Check

Standardization rescales a column so it has a mean of 0 and a standard deviation
of 1. The formula is z equals x minus the mean, divided by the standard
deviation.

This was done with StandardScaler on a copy of the cleaned data, so the original
frame was not modified.

| Column | Mean before | Std before | Mean after | Std after |
| --- | --- | --- | --- | --- |
| age | 29.32 | 12.98 | 0.000 | 1.001 |
| fare | 32.10 | 49.70 | 0.000 | 1.001 |

Both columns land at approximately mean 0 and standard deviation 1, which
confirms the transformation worked. The shape of each distribution is unchanged,
only its scale, so fare is still right skewed afterwards.

The reason this matters is the size difference before scaling. Fare has a
standard deviation of 49.70 against age's 12.98, so on the raw scale a
one unit change in fare and a one unit change in age are not comparable at all.
Models that measure distance or fit coefficients are affected by that imbalance.

This section is an exploratory check only. It does not feed the modeling
pipeline, which performs its own scaling fitted on the training data alone, for
the reason given in Section 9.

---

## Section 8 - Train and Test Split

The data is split into a training set the model learns from and a test set it is
judged on, in an 80 to 20 ratio, stratified on survived.

Stratification matters here because the target is imbalanced.

| Set | Did not survive | Survived |
| --- | --- | --- |
| Original | 61.62 percent | 38.38 percent |
| Training | 61.66 percent | 38.34 percent |
| Testing | 61.45 percent | 38.55 percent |

All three rows match closely, which confirms stratification did its job.

Without stratification, a random split could land noticeably more survivors in
one set than the other. That would make recall and F1 on the test set partly an
accident of the split rather than a property of the model, and rerunning with a
different random seed would move the scores around for no real reason.

The split happens before any preprocessing. That ordering is not optional and it
is the subject of the next section.

---

## Section 9 - The Preprocessing Pipeline

Preprocessing means filling remaining missing values, turning text into numbers
and putting the numeric columns on a common scale.

The strict rule is that every preprocessing step must be fitted on the training
data only, and the test data must only be transformed using what was learned from
the training data.

The reason is data leakage. If the median used to fill ages were computed over
the whole dataset, that median would carry information from test rows into the
training process. The model would then be evaluated on data it had indirectly
already seen, and the reported score would be optimistic in a way that would not
survive contact with genuinely new passengers.

Rather than trusting the code to be written in the right order every time, the
rule is enforced structurally with a ColumnTransformer inside a Pipeline.

| Group | Columns | Step 1 | Step 2 |
| --- | --- | --- | --- |
| Numeric | age, fare, sibsp, parch, pclass | SimpleImputer with the median strategy | StandardScaler |
| Categorical | sex, embarked | SimpleImputer with the most frequent strategy | OneHotEncoder with handle_unknown set to ignore |

The features chosen are pclass, sex, age, sibsp, parch, fare and embarked, and
the target is survived.

Note which columns are deliberately absent. alive is the word form of survived
and would hand the model the answer. class duplicates pclass, embark_town
duplicates embarked, and adult_male and alone are derived from columns already
included.

Two settings are worth calling out.

The median strategy is used for age here for the same reason as in Section 3, the
right skew. The most frequent strategy is used for the categorical columns
because a median has no meaning for a port code.

handle_unknown='ignore' on the encoder means that a category never seen during
training produces a row of zeros rather than raising an error. Without it, the
saved pipeline in Section 15 would crash on a passenger from an unexpected port
instead of degrading gracefully.

---

## Section 10 - Training Three Classifiers

Three models were trained on the identical split, each wrapped in the same
preprocessor so all three saw exactly the same input.

| Model | How it works | Why it is included |
| --- | --- | --- |
| Logistic Regression | Fits a straight boundary between survived and not survived and outputs a probability | A simple interpretable baseline |
| Decision Tree | Asks a series of yes or no questions, for example is the passenger female, then which class | Easy to read and to draw |
| Random Forest | Builds many decision trees and combines their votes | Averaging many trees reduces the overfitting a single tree is prone to |

The decision tree is additionally drawn with plot_tree, with feature names and
class names labelled so the splits can be read directly off the figure.

Using one shared preprocessor for all three is what makes the comparison fair. If
each model had its own preprocessing, a difference in scores could come from the
preprocessing rather than the model.

---

## Section 11 - Evaluating the Three Models

Each model was evaluated on the same test set of 179 passengers, 110 of whom did
not survive and 69 of whom did.

The confusion matrices are below. Reading them, the top left is a correct
prediction of did not survive, the bottom right is a correct prediction of
survived, the top right is a false alarm, and the bottom left is a missed
survivor.

| Model | Correct, did not survive | False alarm | Missed survivor | Correct, survived |
| --- | --- | --- | --- | --- |
| Logistic Regression | 98 | 12 | 23 | 46 |
| Decision Tree | 95 | 15 | 18 | 51 |
| Random Forest | 97 | 13 | 21 | 48 |

The metrics that follow are all computed from those four numbers.

| Metric | What it answers |
| --- | --- |
| Accuracy | Of all predictions, how many were right |
| Precision | Of the passengers predicted to survive, how many actually did |
| Recall | Of the passengers who actually survived, how many the model found |
| F1 Score | The balance between precision and recall |
| AUC | How well the model ranks survivors above non survivors across every threshold |

| Model | Accuracy | Precision | Recall | F1 Score | AUC |
| --- | --- | --- | --- | --- | --- |
| Logistic Regression | 0.804 | 0.793 | 0.667 | 0.724 | 0.844 |
| Decision Tree | 0.816 | 0.773 | 0.739 | 0.756 | 0.797 |
| Random Forest | 0.810 | 0.787 | 0.696 | 0.738 | 0.826 |

The trade off is visible directly in the confusion matrices. Logistic Regression
misses 23 survivors while the Decision Tree misses only 18, which is why the tree
leads on recall. In exchange the tree raises false alarms from 12 to 15, which is
why it trails on precision.

An ROC curve for all three models was plotted on one chart. Logistic Regression
has the best AUC at 0.844 despite the lowest accuracy. That combination is not a
contradiction. AUC judges how well a model ranks passengers by risk across all
thresholds, while accuracy judges the hard yes or no decisions at the single
default threshold of 0.5. Logistic Regression ranks well but converts that
ranking into slightly worse decisions at 0.5.

---

## Section 12 - Handling the Class Imbalance

The target is imbalanced at 549 non survivors to 342 survivors, or 61.62 percent
to 38.38 percent. An imbalance like this pushes a model towards the majority
class, because predicting did not survive every time already scores 61.6 percent
accuracy.

Logistic Regression was retrained three ways to compare strategies.

| Strategy | What it does |
| --- | --- |
| Baseline | No adjustment at all |
| class_weight='balanced' | Tells the model to weight errors on the minority class more heavily, so missing a survivor costs more than a false alarm |
| SMOTE | Creates synthetic minority rows by interpolating between real survivors, until the training set is balanced |

| Strategy | Precision | Recall | F1 Score |
| --- | --- | --- | --- |
| Baseline | 0.793 | 0.667 | 0.724 |
| class_weight='balanced' | 0.730 | 0.783 | 0.755 |
| SMOTE | 0.740 | 0.783 | 0.761 |

SMOTE was applied to the training fold only. This is essential. Generating
synthetic passengers before the split, or on the test set, would put invented
rows into the evaluation and the resulting score would be measuring the model
against data that was partly manufactured from the answers.

Reading the results, both strategies trade precision for recall and both beat the
baseline on F1. Recall rises from 0.667 to 0.783 in both cases, meaning roughly
eight more real survivors are found out of 69, while precision drops by about
0.05 to 0.06.

class_weight='balanced' and SMOTE land very close together at 0.755 and 0.761.
That is expected, since they attack the same problem from two directions, one by
reweighting the loss function and the other by adding rows.

Between the two, class_weight='balanced' is the better practical choice. It
reaches essentially the same result with a single parameter, adds no synthetic
data, and costs nothing in training time, whereas SMOTE enlarges the training set
with interpolated passengers who never existed.

---

## Section 13 - Hyperparameter Tuning

Hyperparameters are the settings chosen before training rather than learned from
the data. GridSearchCV tries every combination and keeps the best.

Three Random Forest parameters were searched.

| Parameter | What it controls | Values tried |
| --- | --- | --- |
| n_estimators | How many trees are in the forest | 50, 100, 200 |
| max_depth | How deep each tree may grow | None meaning unlimited, 5, 10, 20 |
| max_features | How many features each split may consider | sqrt, log2, None meaning all |

The search used 5-fold cross validation, meaning the training data was split into
five parts and each combination was trained five times, each time holding out a
different fifth for validation.

| Result | Value |
| --- | --- |
| Best max_depth | 5 |
| Best max_features | None |
| Best n_estimators | 100 |
| Best cross validation score | 0.8189 |
| OOB score | 0.8188 |

The winning max_depth of 5 is the most informative result here. Unlimited depth
was among the options and lost, which means the shallower forest generalised
better. Trees allowed to grow without limit memorise individual passengers rather
than learning patterns.

The OOB score, or out of bag score, is a second honest estimate obtained for
free. Each tree in a Random Forest is trained on a random sample of rows, so the
rows left out of a given tree can be used to test that tree. It requires
oob_score=True to be set when the classifier is created.

The two estimates agree almost exactly, 0.8189 from cross validation and 0.8188
from OOB. Two independent methods landing within 0.0001 of each other is good
evidence that roughly 0.82 is the model's real level and not an artefact of one
particular split.

---

## Section 14 - Regression Side Task

As a separate task, a multivariate linear regression was built to predict fare
rather than survival. The features were pclass, sex, age, sibsp, parch and
embarked.

This task uses its own train and test split, and all of its variables are
prefixed with fare_ so they cannot overwrite anything belonging to the
classification pipeline.

| Metric | Value | What it means |
| --- | --- | --- |
| MAE | 20.809 | On average the predicted fare is about 20.81 away from the real fare |
| RMSE | 30.473 | The same idea but squaring errors first, so large mistakes count much more |
| R squared | 0.400 | The features explain about 40 percent of the variation in fare |
| Adjusted R squared | 0.368 | R squared corrected for the number of features used, always slightly lower |

RMSE sitting well above MAE, 30.47 against 20.81, is itself a finding. If every
error were about the same size the two would be close. The gap means a minority
of very large errors is dominating, which points at the expensive tickets.

The residual plot confirms it. Residuals fan outward as the predicted fare rises,
a pattern called heteroscedasticity, which means the error variance is not
constant.

| Check | Value |
| --- | --- |
| Residual standard deviation, lowest quartile of predicted fare | 7.49 |
| Residual standard deviation, highest quartile of predicted fare | 50.96 |
| Correlation between absolute residual and predicted fare | 0.548 |

The residual spread grows almost sevenfold from the cheapest quartile to the most
expensive. The model predicts cheap tickets consistently and expensive ones
poorly.

This matters beyond describing the plot. Constant error variance is one of the
assumptions behind ordinary least squares, so with it violated the standard
errors reported by the model are understated and any confidence interval built
from them is too narrow. The usual remedy is to model the logarithm of fare
instead of fare itself, which compresses the expensive tail.

---

## Section 15 - Final Comparison and Recommendation

Classification metrics.

| Model | Accuracy | Precision | Recall | F1 Score | AUC |
| --- | --- | --- | --- | --- | --- |
| Logistic Regression | 0.804 | 0.793 | 0.667 | 0.724 | 0.844 |
| Decision Tree | 0.816 | 0.773 | 0.739 | 0.756 | 0.797 |
| Random Forest | 0.810 | 0.787 | 0.696 | 0.738 | 0.826 |

Regression metrics.

| Model | MAE | RMSE | R squared | Adjusted R squared |
| --- | --- | --- | --- | --- |
| Linear Regression | 20.809 | 30.473 | 0.400 | 0.368 |

The two tables are kept separate on purpose. Classification and regression
metrics are on completely different scales and measure different things, so no
number in the first table is comparable to any number in the second.

The recommendation is the Decision Tree.

| Reason | Detail |
| --- | --- |
| Leads on accuracy | 0.816 against 0.810 and 0.804 |
| Leads on recall | 0.739 against 0.696 and 0.667 |
| Leads on F1 | 0.756 against 0.738 and 0.724 |
| Recall is the metric that matters most here | Failing to identify a survivor is the costlier error in this framing |
| The trade is favourable | It gains 0.072 of recall while giving up only 0.020 of precision against Logistic Regression |
| It is the simplest to explain | The splits can be read directly off the plotted tree |

Two honest caveats go with that choice.

Logistic Regression has the clearly better AUC at 0.844 against 0.797. If the
deliverable were a calibrated probability, for example to rank passengers by risk
and set the threshold later, Logistic Regression would be the better model. The
Decision Tree wins at the default 0.5 threshold specifically.

The Random Forest sits between the other two on every single metric without
leading on any of them, so it earns no place over the simpler and more
interpretable tree despite being the more sophisticated method.

---

## Section 16 - Saving and Reloading the Pipeline

The trained Decision Tree pipeline is saved to disk with joblib.dump as
titanic_survival_pipeline.pkl.

What is saved is the complete pipeline, the ColumnTransformer with its imputers,
encoder and scaler together with the fitted DecisionTreeClassifier, as one
object.

Saving the classifier alone would be a mistake. The classifier expects scaled
numeric columns and one hot encoded categories, so every future caller would have
to reproduce the exact preprocessing by hand before predicting. Any small
difference, a different imputation median or a different category order, would
silently produce wrong predictions rather than an error.

To prove the saved artifact is self sufficient, it was reloaded with joblib.load
and asked to predict on raw, completely unpreprocessed passenger rows, including
one with a missing age.

```
pclass=3 sex=male   age=22.0 -> survived=0 (probability 0.00)
pclass=1 sex=female age=38.0 -> survived=1 (probability 1.00)
pclass=2 sex=female age=nan  -> survived=1 (probability 1.00)

Reloaded pipeline test accuracy: 0.8156424581005587
In-memory pipeline test accuracy: 0.8156424581005587
Same predictions on the test set: True
```

Three things are confirmed by that output. The third passenger has a missing age
and still produces a prediction, which shows the imputer travelled inside the
saved file. The two accuracies are identical to every decimal place. And the
predictions match on every row of the test set, not merely the totals, which
rules out two different sets of errors happening to average to the same score.

---

## Section 17 - Summary of Assignment Requirements

| Requirement | Where it is done | Status |
| --- | --- | --- |
| Load and profile the dataset | Section 2 | 891 rows, 15 columns, shape, info and describe |
| Measure and handle missing values | Section 3 | Threshold rule applied to 4 columns |
| Univariate analysis with outliers and skew | Section 4 | Histograms, box plots, IQR counts, mean median mode |
| Bivariate analysis and correlation | Section 5 | Survival rates plus a 6 by 6 heatmap |
| Multivariate data story | Section 6 | Five connected charts |
| Standardization check | Section 7 | Mean 0 and std 1 confirmed |
| Stratified train and test split | Section 8 | 80 to 20, proportions preserved |
| Preprocessing pipeline with no leakage | Section 9 | ColumnTransformer inside a Pipeline |
| Train at least three classifiers | Section 10 | Logistic Regression, Decision Tree, Random Forest |
| Full evaluation including ROC and AUC | Section 11 | Confusion matrices plus five metrics each |
| Imbalance handling comparison | Section 12 | Baseline, class weight, SMOTE |
| Hyperparameter tuning | Section 13 | GridSearchCV, 5-fold, with OOB score |
| Regression side task | Section 14 | Linear regression on fare with a residual check |
| Final comparison and recommendation | Section 15 | Decision Tree, with caveats stated |
| Save and reload the pipeline | Section 16 | joblib, verified on raw rows |
