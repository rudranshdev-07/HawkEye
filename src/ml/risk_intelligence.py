import numpy as np
import pandas as pd
from typing import Dict, Any, List, Union
from src.utils.logging_config import logger
from src.ml.preprocessing import CrimePreprocessor

# Define Category Severity Weights
# Higher weights represent more severe/violent crimes that pose a higher risk to public safety.
CRIME_SEVERITY_WEIGHTS: Dict[str, float] = {
    # Violent / Personal Crimes (Critical Severity)
    "ASSAULT": 1.5,
    "ASSUALT": 1.5, # Handle common typo
    "BATTERY": 1.5,
    "ROBBERY": 1.5,
    "WEAPONS VIOLATION": 1.5,
    
    # Property / Substance Crimes (Medium Severity)
    "BURGLARY": 1.0,
    "MOTOR VEHICLE THEFT": 1.0,
    "NARCOTICS": 1.0,
    
    # Minor / Financial / Other Crimes (Low Severity)
    "THEFT": 0.7,
    "CRIMINAL DAMAGE": 0.7,
    "DECEPTIVE PRACTICE": 0.7,
    "OTHER OFFENSE": 0.7
}
DEFAULT_SEVERITY_WEIGHT = 0.7

def get_severity_weight(category: str) -> float:
    """
    Returns the severity weight for a given crime category.
    """
    clean_cat = str(category).strip().upper()
    return CRIME_SEVERITY_WEIGHTS.get(clean_cat, DEFAULT_SEVERITY_WEIGHT)

class RiskIntelligenceLayer:
    """
    Combines machine learning arrest predictions with qualitative severity metrics
    to output composite risk assessments and levels for crime incidents.
    """
    def __init__(self, preprocessor: CrimePreprocessor, model: Any):
        self.preprocessor = preprocessor
        self.model = model

    def assess_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Predicts arrest probability, calculates composite risk score,
        and assigns risk level classifications.
        
        Returns a copy of the input DataFrame with the following additional columns:
          - arrest_probability: Probability of arrest (model output)
          - risk_score: Normalized composite risk score [0, 1]
          - risk_level: LOW, MEDIUM, HIGH, or CRITICAL
        """
        logger.info(f"Assessing risk for {len(df)} records...")
        df_out = df.copy()
        
        # 1. Preprocess data
        X_processed = self.preprocessor.transform(df_out)
        
        # 2. Predict arrest probabilities
        if hasattr(self.model, "predict_proba"):
            # Probabilities of class 1 (arrest is True)
            arrest_probs = self.model.predict_proba(X_processed)[:, 1]
        else:
            # Fallback if estimator doesn't support probability
            arrest_probs = self.model.predict(X_processed).astype(float)
            
        df_out["arrest_probability"] = arrest_probs
        
        # 3. Compute risk score and level
        risk_scores = []
        risk_levels = []
        
        # For each row, calculate composite risk
        categories = df_out["category"].values if "category" in df_out.columns else ["UNKNOWN"] * len(df_out)
        
        for idx, cat in enumerate(categories):
            prob_arr = arrest_probs[idx]
            severity_w = get_severity_weight(cat)
            
            # Risk Score Formula:
            # High risk = High severity and LOW probability of arrest (offender remains at large)
            # Max possible score = 1.5 * 1.0 = 1.5
            unnormalized_score = severity_w * (1.0 - prob_arr)
            
            # Normalize to [0, 1] range
            normalized_score = round(float(unnormalized_score / 1.5), 4)
            risk_scores.append(normalized_score)
            
            # Classify Risk Level
            if normalized_score < 0.25:
                level = "LOW"
            elif normalized_score < 0.50:
                level = "MEDIUM"
            elif normalized_score < 0.75:
                level = "HIGH"
            else:
                level = "CRITICAL"
                
            risk_levels.append(level)
            
        df_out["risk_score"] = risk_scores
        df_out["risk_level"] = risk_levels
        
        logger.info(f"Risk assessment complete: assigned {risk_levels.count('CRITICAL')} CRITICAL, {risk_levels.count('HIGH')} HIGH, {risk_levels.count('MEDIUM')} MEDIUM, {risk_levels.count('LOW')} LOW labels.")
        return df_out

    def generate_risk_report(self, df_assessed: pd.DataFrame) -> Dict[str, Any]:
        """
        Compiles general aggregate risk analytics from assessed crime records.
        """
        total = len(df_assessed)
        if total == 0:
            return {"total_assessed": 0, "distribution": {}, "averages": {}}
            
        level_counts = df_assessed["risk_level"].value_counts().to_dict()
        level_pcts = {str(k): round((int(v) / total) * 100, 2) for k, v in level_counts.items()}
        
        avg_risk = float(df_assessed["risk_score"].mean())
        avg_arr_prob = float(df_assessed["arrest_probability"].mean())
        
        # Breakdown by category
        cat_risk = {}
        if "category" in df_assessed.columns:
            grouped = df_assessed.groupby("category")
            for cat, group in grouped:
                cat_risk[str(cat)] = {
                    "count": len(group),
                    "avg_risk_score": round(float(group["risk_score"].mean()), 4),
                    "avg_arrest_probability": round(float(group["arrest_probability"].mean()), 4)
                }
                
        return {
            "total_assessed": total,
            "overall_averages": {
                "risk_score": round(avg_risk, 4),
                "arrest_probability": round(avg_arr_prob, 4)
            },
            "risk_level_counts": {str(k): int(v) for k, v in level_counts.items()},
            "risk_level_percentages": level_pcts,
            "category_breakdown": cat_risk
        }
