import joblib
import numpy as np
from core.management.commands.extract_user_ml_data import extract_user_features, FEATURES
import os

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'loan_approval_model.pkl')

class LoanMLPredictor:
    def __init__(self):
        self.model = joblib.load(MODEL_PATH)

    def predict_user(self, user_profile):
        features = extract_user_features(user_profile)
        X = np.array(features).reshape(1, -1)
        proba = self.model.predict_proba(X)[0][1]  # Probability of being a good borrower
        pred = self.model.predict(X)[0]
        return {
            'prediction': int(pred),
            'probability': float(proba)
        }
