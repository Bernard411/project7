

import os
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
from sklearn.utils import resample

# Robust file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SYNTH_PATH = os.path.join(BASE_DIR, 'synthetic_loan_data.csv')
REAL_PATH = os.path.join(BASE_DIR, '../real_user_loan_data.csv')


# Load synthetic and real data
synth = pd.read_csv(SYNTH_PATH)
try:
    real = pd.read_csv(REAL_PATH)
    data = pd.concat([synth, real], ignore_index=True)
except Exception:
    data = synth

# Balance the dataset by oversampling the minority class
majority = data[data['target'] == 0]
minority = data[data['target'] == 1]
if len(minority) > 0:
    minority_upsampled = resample(minority, replace=True, n_samples=len(majority), random_state=42)
    data = pd.concat([majority, minority_upsampled], ignore_index=True)

X = data.drop('target', axis=1)
y = data['target']

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
clf = RandomForestClassifier(n_estimators=200, random_state=42, class_weight='balanced')
clf.fit(X_train, y_train)

# Evaluate
y_pred = clf.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"Test Accuracy: {acc:.4f}")
print(classification_report(y_test, y_pred))

# Save model if accuracy is high
if acc >= 0.90:
    joblib.dump(clf, 'loan_approval_model.pkl')
    print('Model saved as loan_approval_model.pkl')
else:
    print('Model accuracy below 90%, not saved.')
