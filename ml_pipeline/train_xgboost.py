import os
import pandas as pd
import joblib

from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
from xgboost import XGBClassifier


df = pd.read_csv("ml_pipeline/data/rely_lis_model_features_v10.csv")

TARGET_COL = "anomaly_label_text"

FEATURES = [
    'result_value_num',
    'ref_min_parsed',
    'ref_max_parsed',
    'biomarker_code',
    'test_panel',
    'result_month'
]

df_clean = df[FEATURES + [TARGET_COL, 'lab_id']].copy()

df_clean['biomarker_code'] = df_clean['biomarker_code'].fillna("UNKNOWN")
df_clean['test_panel'] = df_clean['test_panel'].fillna("UNKNOWN")

bio_encoder = LabelEncoder()
panel_encoder = LabelEncoder()
target_encoder = LabelEncoder()

df_clean['biomarker_code'] = bio_encoder.fit_transform(df_clean['biomarker_code'])
df_clean['test_panel'] = panel_encoder.fit_transform(df_clean['test_panel'])

y = target_encoder.fit_transform(df_clean[TARGET_COL])
X = df_clean[FEATURES]
groups = df_clean['lab_id']

gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(gss.split(X, y, groups))

X_train = X.iloc[train_idx]
X_test = X.iloc[test_idx]
y_train = y[train_idx]
y_test = y[test_idx]

model = XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective='multi:softprob',
    eval_metric='mlogloss',
    tree_method='hist',
    random_state=42
)

model.fit(X_train, y_train)

y_pred = model.predict(X_test)

print("CLASSIFICATION REPORT")


print(classification_report(
    y_test,
    y_pred,
    target_names=target_encoder.classes_
))

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ARTIFACT_DIR = os.path.join(BASE_DIR, "backend_api", "artifacts")

os.makedirs(ARTIFACT_DIR, exist_ok=True)

joblib.dump(model, os.path.join(ARTIFACT_DIR, "xgboost_model.joblib"))
joblib.dump(bio_encoder, os.path.join(ARTIFACT_DIR, "bio_encoder.joblib"))
joblib.dump(panel_encoder, os.path.join(ARTIFACT_DIR, "panel_encoder.joblib"))
joblib.dump(target_encoder, os.path.join(ARTIFACT_DIR, "target_encoder.joblib"))

print("\n artifacts saved")