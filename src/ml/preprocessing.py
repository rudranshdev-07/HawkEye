import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from src.ml.feature_engineering import CrimeFeatureEngineer
from src.utils.logging_config import logger

class CrimePreprocessor(BaseEstimator, TransformerMixin):
    """
    Combines feature engineering and standard preprocessing (scaling/encoding)
    into a single, reusable scikit-learn estimator.
    """
    def __init__(
        self,
        dbscan_eps_meters: float = 300.0,
        dbscan_min_samples: int = 15,
        num_hotspots: int = 10
    ):
        self.dbscan_eps_meters = dbscan_eps_meters
        self.dbscan_min_samples = dbscan_min_samples
        self.num_hotspots = num_hotspots
        
        self.feature_engineer = CrimeFeatureEngineer(
            dbscan_eps_meters=dbscan_eps_meters,
            dbscan_min_samples=dbscan_min_samples,
            num_hotspots=num_hotspots
        )
        self.column_transformer: ColumnTransformer = None
        self.numerical_cols_: List[str] = []
        self.categorical_cols_: List[str] = []

    def fit(self, X: pd.DataFrame, y=None):
        """
        Fits both the feature engineer and the scaling/encoding pipelines.
        """
        logger.info("Fitting CrimePreprocessor...")
        
        # 1. Fit & transform feature engineer to get columns
        X_engineered = self.feature_engineer.fit_transform(X, y)
        
        # 2. Identify numerical and categorical columns dynamically
        # Exclude metadata and target columns from feature list
        exclude_cols = ["crime_id", "date", "description", "arrest", "domestic"]
        
        numerical_features = []
        categorical_features = []
        
        # We handle 'domestic' as a categorical feature, but exclude metadata columns
        for col in X_engineered.columns:
            if col in exclude_cols:
                continue
            if pd.api.types.is_numeric_dtype(X_engineered[col]) and not pd.api.types.is_bool_dtype(X_engineered[col]):
                numerical_features.append(col)
            else:
                categorical_features.append(col)
                
        # Also explicitly add 'domestic' as a categorical binary feature
        if "domestic" in X_engineered.columns:
            categorical_features.append("domestic")
            
        self.numerical_cols_ = numerical_features
        self.categorical_cols_ = categorical_features
        
        logger.info(f"Dynamically detected {len(self.numerical_cols_)} numerical features and {len(self.categorical_cols_)} categorical features for ML.")
        
        # 3. Construct the ColumnTransformer
        num_pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ])
        
        cat_pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='constant', fill_value='UNKNOWN')),
            ('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
        ])
        
        self.column_transformer = ColumnTransformer(transformers=[
            ('num', num_pipeline, self.numerical_cols_),
            ('cat', cat_pipeline, self.categorical_cols_)
        ])
        
        # Fit ColumnTransformer on engineered data
        self.column_transformer.fit(X_engineered, y)
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        """
        Transforms the input DataFrame by running feature engineering and column scaling/encoding.
        """
        if self.column_transformer is None:
            raise ValueError("CrimePreprocessor must be fitted before calling transform.")
            
        # 1. Engineer features
        X_engineered = self.feature_engineer.transform(X)
        
        # 2. Apply scaling/encoding ColumnTransformer
        return self.column_transformer.transform(X_engineered)

    def get_feature_names_out(self) -> List[str]:
        """
        Returns feature names after preprocessing.
        """
        if self.column_transformer is None:
            raise ValueError("CrimePreprocessor must be fitted to get feature names.")
        return list(self.column_transformer.get_feature_names_out())

def prepare_data_splits(
    df: pd.DataFrame,
    target_col: str = "arrest",
    test_size: float = 0.2,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Splits the crime dataset into train and test sets, stratifying on the target variable
    to handle class imbalances.
    """
    logger.info(f"Preparing data splits. Splitting dataset with size={len(df)} into train/test (test_size={test_size}).")
    
    if target_col not in df.columns:
        logger.error(f"Target column '{target_col}' not found in DataFrame columns: {list(df.columns)}")
        raise ValueError(f"Target column '{target_col}' is missing.")
        
    # Standardize target to boolean/int values for split
    # Simple check to drop any rows where target is missing
    df_clean = df.dropna(subset=[target_col]).copy()
    
    X = df_clean.drop(columns=[target_col])
    y = df_clean[target_col].astype(int)
    
    # Check class counts to ensure we can stratify
    class_counts = y.value_counts()
    if len(class_counts) < 2 or class_counts.min() < 2:
        logger.warning("Target class counts are too small for stratified splitting. Performing unstratified split.")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
    logger.info(f"Data split complete. Train features size: {X_train.shape}, Test features size: {X_test.shape}")
    return X_train, X_test, y_train, y_test
