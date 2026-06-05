import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from src.utils.logging_config import logger
from src.ml.preprocessing import CrimePreprocessor

def train_and_compare_models(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    random_state: int = 42
) -> Tuple[Dict[str, Dict[str, Any]], str, Any]:
    """
    Trains and compares Random Forest, Gradient Boosting, Decision Tree, and Logistic Regression.
    Returns:
      1. A dictionary of evaluation metrics for each model.
      2. The name of the best-performing model.
      3. The trained best model instance.
    """
    logger.info("Initializing models for comparison...")
    
    models = {
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=10, random_state=random_state),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=random_state),
        "Decision Tree": DecisionTreeClassifier(max_depth=10, random_state=random_state),
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=random_state)
    }
    
    evaluation_results = {}
    best_f1 = -1.0
    best_model_name = None
    best_model_instance = None
    
    for name, clf in models.items():
        logger.info(f"Training {name} classifier...")
        try:
            # Fit model
            clf.fit(X_train, y_train)
            
            # Predict
            y_pred = clf.predict(X_test)
            
            # Predict probabilities for precision/recall curves or risk layers
            if hasattr(clf, "predict_proba"):
                y_prob = clf.predict_proba(X_test)[:, 1]
            else:
                y_prob = y_pred.astype(float)
                
            # Compute evaluation metrics
            acc = accuracy_score(y_test, y_pred)
            prec = precision_score(y_test, y_pred, zero_division=0)
            rec = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            cm = confusion_matrix(y_test, y_pred).tolist()
            
            evaluation_results[name] = {
                "accuracy": round(float(acc), 4),
                "precision": round(float(prec), 4),
                "recall": round(float(rec), 4),
                "f1_score": round(float(f1), 4),
                "confusion_matrix": cm,
                "estimator": clf
            }
            
            logger.info(f"{name} Results: Acc: {acc:.4f} | Prec: {prec:.4f} | Rec: {rec:.4f} | F1: {f1:.4f}")
            
            # Select best model based on F1 Score
            if f1 > best_f1:
                best_f1 = f1
                best_model_name = name
                best_model_instance = clf
                
        except Exception as e:
            logger.error(f"Error training model '{name}': {str(e)}", exc_info=True)
            
    if best_model_name is None:
        raise ValueError("All model training attempts failed.")
        
    logger.info(f"Model comparison complete. Best performer: {best_model_name} with F1-Score: {best_f1:.4f}")
    return evaluation_results, best_model_name, best_model_instance

def save_serialized_pipeline(
    preprocessor: CrimePreprocessor,
    model: Any,
    models_dir: str = "models"
) -> Tuple[str, str]:
    """
    Saves the preprocessor pipeline and the trained model to files using joblib.
    Ensures that target directory exists.
    """
    if not os.path.exists(models_dir):
        os.makedirs(models_dir)
        logger.info(f"Created models persistence directory: {models_dir}")
        
    preprocessor_path = os.path.join(models_dir, "preprocessing_pipeline.pkl")
    model_path = os.path.join(models_dir, "best_model.pkl")
    
    logger.info(f"Saving preprocessing pipeline to: {preprocessor_path}")
    joblib.dump(preprocessor, preprocessor_path)
    
    logger.info(f"Saving best model to: {model_path}")
    joblib.dump(model, model_path)
    
    return preprocessor_path, model_path

def load_serialized_pipeline(models_dir: str = "models") -> Tuple[CrimePreprocessor, Any]:
    """
    Loads and returns the serialized preprocessor and model from disk.
    """
    preprocessor_path = os.path.join(models_dir, "preprocessing_pipeline.pkl")
    model_path = os.path.join(models_dir, "best_model.pkl")
    
    if not os.path.exists(preprocessor_path):
        logger.error(f"Preprocessor file not found at: {preprocessor_path}")
        raise FileNotFoundError(f"Serialized preprocessor not found at {preprocessor_path}")
        
    if not os.path.exists(model_path):
        logger.error(f"Model file not found at: {model_path}")
        raise FileNotFoundError(f"Serialized model not found at {model_path}")
        
    logger.info("Loading preprocessing pipeline and model from disk...")
    preprocessor = joblib.load(preprocessor_path)
    model = joblib.load(model_path)
    
    return preprocessor, model
