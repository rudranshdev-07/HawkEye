import argparse
import json
import os
import pandas as pd
from src.ml.preprocessing import CrimePreprocessor, prepare_data_splits
from src.ml.models import train_and_compare_models, save_serialized_pipeline
from src.ml.risk_intelligence import RiskIntelligenceLayer
from src.utils.logging_config import logger

def main():
    parser = argparse.ArgumentParser(description="HawkEye Machine Learning and Risk Intelligence Pipeline")
    parser.add_argument(
        "--processed-path",
        type=str,
        default="data/processed/crime_processed_data.csv",
        help="Path to the cleaned/processed crime CSV file"
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default="models",
        help="Directory to save serialized models/preprocessors"
    )
    parser.add_argument(
        "--reports-dir",
        type=str,
        default="reports/ml",
        help="Directory to save evaluation reports"
    )
    parser.add_argument(
        "--risk-path",
        type=str,
        default="data/processed/crime_risk_assessed.csv",
        help="Path to save the risk-assessed crime CSV file"
    )
    
    args = parser.parse_args()
    
    logger.info("Starting HawkEye Machine Learning Pipeline...")
    
    if not os.path.exists(args.processed_path):
        logger.error(f"Cleaned dataset not found: {args.processed_path}")
        print(f"\nERROR: Processed dataset not found at {args.processed_path}. Please run Phase 1 first!\n")
        exit(1)
        
    try:
        # 1. Load Dataset
        logger.info(f"Loading cleaned dataset from {args.processed_path}")
        df = pd.read_csv(args.processed_path)
        
        # Ensure 'date' is cast properly
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        
        # 2. Split Data
        X_train, X_test, y_train, y_test = prepare_data_splits(
            df=df, target_col="arrest", test_size=0.2, random_state=42
        )
        
        # 3. Fit and Transform Preprocessing Pipeline
        logger.info("Fitting preprocessing pipeline on training data...")
        preprocessor = CrimePreprocessor(dbscan_eps_meters=300.0, dbscan_min_samples=15, num_hotspots=10)
        preprocessor.fit(X_train, y_train)
        
        X_train_processed = preprocessor.transform(X_train)
        X_test_processed = preprocessor.transform(X_test)
        
        # 4. Train, Compare, and Evaluate Models
        eval_results, best_name, best_model = train_and_compare_models(
            X_train_processed, y_train.values, X_test_processed, y_test.values, random_state=42
        )
        
        # 5. Persist Best Model and Pipeline
        preprocessor_path, model_path = save_serialized_pipeline(preprocessor, best_model, args.models_dir)
        
        # 6. Apply Risk Intelligence Layer on Entire Dataset
        logger.info("Instantiating Risk Intelligence Layer and predicting entire dataset...")
        risk_layer = RiskIntelligenceLayer(preprocessor, best_model)
        df_risk_assessed = risk_layer.assess_risk(df)
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(args.risk_path), exist_ok=True)
        os.makedirs(args.reports_dir, exist_ok=True)
        
        # Save Risk-Assessed CSV
        df_risk_assessed.to_csv(args.risk_path, index=False)
        logger.info(f"Saved risk-assessed dataset to: {args.risk_path}")
        
        # Compile Reports
        risk_report = risk_layer.generate_risk_report(df_risk_assessed)
        
        # Prepare evaluation report (strip sklearn estimators for serialization)
        serializable_eval = {}
        for m_name, metrics in eval_results.items():
            serializable_eval[m_name] = {k: v for k, v in metrics.items() if k != "estimator"}
            
        ml_report = {
            "best_model": best_name,
            "metrics": serializable_eval,
            "risk_profile": risk_report
        }
        
        # Save JSON Report
        report_path = os.path.join(args.reports_dir, "ml_evaluation_report.json")
        with open(report_path, "w") as f:
            json.dump(ml_report, f, indent=4)
        logger.info(f"Saved machine learning report to: {report_path}")
        
        # 7. Print Console Summary
        print("\n" + "=" * 50)
        print("          HAWKEYE MACHINE LEARNING PIPELINE          ")
        print("=" * 50)
        print(f"Processed Dataset:       {args.processed_path}")
        print(f"Serialized Preprocessor: {preprocessor_path}")
        print(f"Serialized Best Model:   {model_path}")
        print(f"Risk-Assessed Output:    {args.risk_path}")
        print(f"Evaluation JSON Report:  {report_path}")
        print("-" * 50)
        print(f"Best Model Selected:     {best_name} ({ml_report['metrics'][best_name]['f1_score']:.4f} F1)")
        print("-" * 50)
        print("Model Performance Summary (sorted by F1-Score):")
        sorted_models = sorted(ml_report["metrics"].items(), key=lambda x: x[1]["f1_score"], reverse=True)
        for m_name, metrics in sorted_models:
            print(f"  - {m_name:20} | F1: {metrics['f1_score']:.4f} | Acc: {metrics['accuracy']:.4f} | Prec: {metrics['precision']:.4f} | Rec: {metrics['recall']:.4f}")
        print("-" * 50)
        print("Risk Profile Summary:")
        print(f"  - Total Incidents:     {risk_report['total_assessed']}")
        print(f"  - Avg Risk Score:      {risk_report['overall_averages']['risk_score']:.4f}")
        print(f"  - Avg Arrest Prob:     {risk_report['overall_averages']['arrest_probability']:.2f}")
        print("Risk Level Breakdown:")
        for lvl, cnt in risk_report["risk_level_counts"].items():
            pct = risk_report["risk_level_percentages"][lvl]
            print(f"  - {lvl:12} {cnt:>6} ({pct}%)")
        print("=" * 50 + "\n")
        
    except Exception as e:
        logger.critical(f"Machine learning execution failed: {str(e)}", exc_info=True)
        print(f"\nERROR: Machine learning execution failed: {str(e)}\n")
        exit(1)

if __name__ == "__main__":
    main()
