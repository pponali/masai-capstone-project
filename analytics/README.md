# Module 2 — Analytics Pipeline

One cohesive pipeline over the Titanic dataset: profile it, clean it, tell a visual story about it, then build and evaluate a predictive-modeling pipeline on the same data.

| File | Description |
| --- | --- |
| `01_eda.ipynb` | Loads the dataset (the single network load), profiles it, cleans it, saves `titanic.csv`, and produces the full EDA story. |
| `02_modeling.ipynb` | Reads that same `titanic.csv` and runs the modeling pipeline, tuning, regression side-task and final save. |
| `titanic.csv` | The committed offline fallback, written by `df.to_csv("titanic.csv", index=False)` immediately after loading. |
| `titanic_survival_pipeline.pkl` | The saved end-to-end pipeline — `ColumnTransformer` + `DecisionTreeClassifier` in a single `Pipeline`. |

## Install and Run

```bash
pip install pandas seaborn matplotlib scikit-learn imbalanced-learn joblib
```

Run `01_eda.ipynb` first, then `02_modeling.ipynb`. The raw dataset is fetched from the network **exactly once**, in cell 1 of `01_eda.ipynb`; every later step — including all of `02_modeling.ipynb` — works from the `titanic.csv` that load produced. There is no second `sns.load_dataset` call anywhere in the module.

---

## Part A — Profiling and Cleaning

### Missing values and the strategy applied to each

Measured on the 891-row raw dataset:

| Column | Missing % | Threshold band | Strategy | Justification |
| --- | ---: | --- | --- | --- |
| `embarked` | 0.22% | under 5% → drop rows | Dropped the 2 affected rows | Losing 2 of 891 rows costs nothing, and imputing a port of embarkation would invent information. |
| `embark_town` | 0.22% | under 5% → drop rows | Dropped with the same rows | Duplicate of `embarked` in text form; the same 2 rows are affected. |
| `age` | 19.87% | 5%–30% → impute | Median imputation | Within the impute band. The median is used rather than the mean because `age` is right-skewed, so the mean is pulled upward by older passengers. |
| `deck` | 77.22% | above the impute band | **Column dropped** | At 77.2% missing, any imputation would be fabricating the majority of the column — whatever value were chosen would dominate the distribution and create a pattern that does not exist in the data. Encoding "missing" as its own category was considered, but that category would simply mean "travelled in third class", information already carried by `pclass`. Dropping is the honest option. |

### Univariate analysis

Histograms and box plots are produced for both `age` and `fare`.

**IQR outlier counts** using `[Q1 − 1.5×IQR, Q3 + 1.5×IQR]`:

| Column | Outliers |
| --- | ---: |
| `age` | 11 |
| `fare` | 116 |

**Fare skewness** — mean **32.10**, median **14.45**, mode **8.05**. The ordering is **mode < median < mean**, which is the signature of a **right-skewed (positively skewed)** distribution: a long tail of expensive first-class tickets drags the mean well above the median, while the bulk of passengers paid single-digit fares.

### Bivariate analysis

Survival rates computed with boolean masking:

| Breakdown | Survival rate |
| --- | ---: |
| Female | 74.04% |
| Male | 18.89% |
| Class 1 | 62.6% |
| Class 2 | 47.3% |
| Class 3 | 24.2% |
| Female, class 1 | 96.74% |
| Female, class 2 | 92.11% |
| Female, class 3 | 50.00% |
| Male, class 1 | 36.89% |
| Male, class 2 | 15.74% |
| Male, class 3 | 13.54% |

The correlation matrix is computed on exactly the six specified columns — `survived`, `pclass`, `age`, `sibsp`, `parch`, `fare` — and rendered with `sns.heatmap`. The boolean flags `adult_male` and `alone` are excluded because they are derived from `sex`/`age` and `sibsp`+`parch` respectively, not independent measurements.

**The two strongest correlations**, ranked by absolute off-diagonal coefficient:

1. **`pclass` ↔ `fare` = −0.549.** The strongest relationship in the matrix, and a definitional one: class 1 is the most expensive ticket and class 3 the cheapest, so as the class *number* rises the fare falls. It confirms the two columns encode much the same underlying thing — a passenger's wealth.
2. **`sibsp` ↔ `parch` = +0.415.** Passengers travelling with siblings or a spouse also tended to have parents or children aboard — both are measuring family group size, which is why the derived `alone` flag is redundant with them.

### Exploratory standardization

`age` and `fare` are standardized with `z = (x − mean) / std` on a copy of the cleaned frame, with a printed before/after summary confirming the transformed columns have mean ≈ 0 and std ≈ 1. This is an EDA sanity check only — the modeling pipeline performs its own train-only scaling and does not consume these columns.

---

## Part B — Modeling

### Split and preprocessing

The split is **stratified on `survived`** and happens **before any preprocessing**. Stratification matters because the classes are imbalanced — **38.38% survived / 61.62% did not**. An unstratified split can drift the minority proportion between train and test, which makes recall and F1 on the test set partly an artefact of the split rather than of the model.

Preprocessing runs inside a `ColumnTransformer` wrapped in a `Pipeline`, so the fit-on-train / transform-on-test boundary is enforced structurally rather than by hand:

* **Numeric** (`age`, `fare`, `sibsp`, `parch`, `pclass`) — median imputation, then `StandardScaler`.
* **Categorical** (`sex`, `embarked`) — most-frequent imputation, then `OneHotEncoder(handle_unknown='ignore')`.

Median imputation is used here for `age` for the same reason as in Part A. `handle_unknown='ignore'` means an unseen category at predict time produces an all-zero row rather than an exception.

### Classification results

Three classifiers on the identical split, each evaluated with a confusion matrix, accuracy, precision, recall, F1 and ROC/AUC. The decision tree is additionally rendered with `plot_tree` using labelled feature and class names.

| Model | Accuracy | Precision | Recall | F1 Score | AUC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Logistic Regression | 0.804 | 0.793 | 0.667 | 0.724 | **0.844** |
| **Decision Tree** | **0.816** | 0.773 | **0.739** | **0.756** | 0.797 |
| Random Forest | 0.810 | 0.787 | 0.696 | 0.738 | 0.826 |

### Imbalance handling

Class balance is 38.38% / 61.62%. Logistic Regression was retrained three ways, with SMOTE applied to the **training fold only** so no synthetic sample can leak into the test set:

| Variant | Precision | Recall | F1 Score |
| --- | ---: | ---: | ---: |
| Baseline | 0.793 | 0.667 | 0.724 |
| `class_weight='balanced'` | 0.730 | 0.783 | 0.755 |
| SMOTE | 0.740 | 0.783 | 0.761 |

**Conclusion.** Both handling strategies trade precision for recall, and both come out ahead on F1. `class_weight='balanced'` and SMOTE land close together (0.755 vs 0.761), which is expected — they attack the same problem, one by reweighting the loss and the other by synthesising minority rows. `class_weight='balanced'` is the better choice in practice: it achieves the same result with a single parameter, adds no synthetic data, and costs nothing at training time, whereas SMOTE enlarges the training set and introduces interpolated passengers that never existed.

### Hyperparameter tuning

`GridSearchCV` (5-fold) over the Random Forest's `n_estimators`, `max_depth` and `max_features`, with the estimator constructed as `RandomForestClassifier(oob_score=True, ...)` so the OOB score is available. Best parameters: `max_depth=5`, `max_features=None`, `n_estimators=100`, with a best CV score of **0.8189** and an **OOB score of 0.8188**.

### Regression side-task

Multivariate linear regression predicting `fare` from `pclass`, `sex`, `age`, `sibsp`, `parch` and `embarked`. All of this section's variables are prefixed `fare_` so they cannot overwrite the classification split.

| Metric | Value |
| --- | ---: |
| MAE | 20.809 |
| RMSE | 30.473 |
| R² | 0.400 |
| Adjusted R² | 0.368 |

RMSE well above MAE indicates a few large errors dominating; R² of 0.400 means the features explain about 40% of the variation in fare.

**Heteroscedasticity: yes, clearly present.** The residual plot funnels outward as the predicted fare rises. The numeric check confirms it — residual standard deviation climbs from **7.49** in the lowest quartile of predicted fare to **50.96** in the highest, and the correlation between absolute residual and predicted fare is **0.548**. The model predicts cheap tickets consistently and expensive ones poorly. Because constant error variance is an OLS assumption, the standard errors here are understated; a log transform of `fare` would be the usual remedy.

---

## Final Model Comparison

Classification and regression metrics are on different scales and are **not** comparable to one another. They are presented as two separate metric groups.

**Classification metrics**

| Model | Accuracy | Precision | Recall | F1 Score | AUC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Logistic Regression | 0.804 | 0.793 | 0.667 | 0.724 | 0.844 |
| Decision Tree | 0.816 | 0.773 | 0.739 | 0.756 | 0.797 |
| Random Forest | 0.810 | 0.787 | 0.696 | 0.738 | 0.826 |

**Regression metrics**

| Model | MAE | RMSE | R² | Adjusted R² |
| --- | ---: | ---: | ---: | ---: |
| Linear Regression | 20.809 | 30.473 | 0.400 | 0.368 |

### Recommendation

I would deploy the **Decision Tree**. It leads on accuracy (0.816 vs 0.810 and 0.804), on recall (0.739 vs 0.696 and 0.667) and on F1 (0.756 vs 0.738 and 0.724) — and recall is the metric that matters most here, since failing to identify a survivor is the costlier error in this framing. Logistic Regression has the best AUC at 0.844 against the tree's 0.797, meaning it ranks passengers by risk more reliably across all thresholds, so it would be the better choice if the output were a calibrated probability rather than a hard label. At the default 0.5 threshold, though, the tree converts that ranking into better decisions: it lifts recall by 0.072 while giving up only 0.020 of precision. The Random Forest sits between the two on every metric without leading on any, so it earns no place over the simpler and more interpretable tree.

---

## Saved Artifact

`titanic_survival_pipeline.pkl` holds the **complete fitted pipeline** — the `ColumnTransformer` (imputers, one-hot encoder, scaler) together with the `DecisionTreeClassifier` — saved as one object with `joblib.dump`.

The final cell reloads it with `joblib.load` and predicts on **raw, unpreprocessed** passenger rows, including one with a missing `age`, to demonstrate the artifact handles imputation, encoding and scaling itself. It confirms the reloaded object reproduces the in-memory pipeline exactly:

```
pclass=3 sex=male   age=22.0 -> survived=0 (probability 0.00)
pclass=1 sex=female age=38.0 -> survived=1 (probability 1.00)
pclass=2 sex=female age=nan  -> survived=1 (probability 1.00)

Reloaded pipeline test accuracy: 0.8156424581005587
In-memory pipeline test accuracy: 0.8156424581005587
Same predictions on the test set: True
```
