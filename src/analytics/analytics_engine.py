import pandas as pd
import numpy as np
from typing import Dict, Any
from src.utils.logging_config import logger

class CrimeAnalyticsEngine:
    """
    Computes spatial, temporal, category, and statistical aggregates on cleaned crime datasets.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._ensure_datetime_columns()

    def _ensure_datetime_columns(self):
        """
        Ensures the 'date' column is cast to datetime and creates sub-fields.
        """
        if "date" not in self.df.columns:
            logger.error("Missing required 'date' column for analytics.")
            raise ValueError("Dataset must contain a 'date' column.")
            
        if not pd.api.types.is_datetime64_any_dtype(self.df["date"]):
            self.df["date"] = pd.to_datetime(self.df["date"], errors="coerce")
            
        # Drop any records where datetime parsing failed (should already be handled, but safety first)
        self.df = self.df.dropna(subset=["date"]).copy()
        
        # Populate helper temporal columns
        self.df["year"] = self.df["date"].dt.year
        self.df["month"] = self.df["date"].dt.month
        self.df["month_name"] = self.df["date"].dt.strftime("%B")
        self.df["day_name"] = self.df["date"].dt.strftime("%A")
        self.df["day_of_week"] = self.df["date"].dt.weekday  # Monday=0, Sunday=6
        self.df["hour"] = self.df["date"].dt.hour

    def run_frequency_analysis(self) -> Dict[str, Any]:
        """
        Computes overall volumes and daily/hourly rates.
        """
        total_crimes = len(self.df)
        if total_crimes == 0:
            return {"total_records": 0, "days_covered": 0, "daily_average": 0.0}
            
        unique_days = self.df["date"].dt.normalize().nunique()
        daily_average = total_crimes / unique_days if unique_days > 0 else 0.0
        
        # Hourly averages
        hourly_counts = self.df.groupby("hour").size()
        avg_per_hour = {int(h): float(c / unique_days) if unique_days > 0 else 0.0 for h, c in hourly_counts.items()}
        
        logger.info(f"Frequency Analysis: {total_crimes} crimes across {unique_days} days. Daily average: {daily_average:.2f}")
        return {
            "total_records": total_crimes,
            "days_covered": unique_days,
            "daily_average": round(float(daily_average), 2),
            "hourly_averages": avg_per_hour
        }

    def run_category_analysis(self) -> Dict[str, Any]:
        """
        Computes distributions and percentages of crimes by category.
        """
        total_crimes = len(self.df)
        if total_crimes == 0:
            return {}

        cat_counts = self.df["category"].value_counts()
        category_stats = {}
        for cat, count in cat_counts.items():
            pct = (count / total_crimes) * 100
            category_stats[str(cat)] = {
                "count": int(count),
                "percentage": round(float(pct), 2)
            }
        
        logger.info(f"Category Analysis: computed stats for {len(category_stats)} distinct categories.")
        return category_stats

    def run_temporal_analysis(self) -> Dict[str, Any]:
        """
        Computes yearly, monthly, weekly, and hourly counts.
        """
        # Yearly
        yearly = self.df.groupby("year").size().to_dict()
        
        # Monthly Seasonality (Month 1-12)
        month_order = ["January", "February", "March", "April", "May", "June", 
                       "July", "August", "September", "October", "November", "December"]
        monthly_counts = self.df.groupby("month_name").size()
        monthly = {m: int(monthly_counts.get(m, 0)) for m in month_order}
        
        # Day of Week
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekly_counts = self.df.groupby("day_name").size()
        weekly = {d: int(weekly_counts.get(d, 0)) for d in day_order}
        
        # Hourly Distribution
        hourly = {int(h): int(count) for h, count in self.df.groupby("hour").size().items()}
        # Fill missing hours
        for h in range(24):
            if h not in hourly:
                hourly[h] = 0
                
        # Chronological Month-Year Trend (e.g. "2023-01")
        self.df["year_month"] = self.df["date"].dt.to_period("M")
        chronological_counts = self.df.groupby("year_month").size().sort_index()
        chronological_trend = {str(ym): int(cnt) for ym, cnt in chronological_counts.items()}
        # Clean up temporary column
        self.df.drop(columns=["year_month"], inplace=True)

        logger.info("Temporal Analysis complete.")
        return {
            "yearly_trends": {str(k): int(v) for k, v in yearly.items()},
            "monthly_seasonality": monthly,
            "weekly_distribution": weekly,
            "hourly_distribution": hourly,
            "chronological_trend": chronological_trend
        }

    def run_location_analysis(self, top_n: int = 10) -> Dict[str, Any]:
        """
        Finds the top crime locations, districts, and wards.
        """
        loc_desc = self.df["location_description"].value_counts().head(top_n).to_dict()
        districts = self.df["district"].value_counts().head(top_n).to_dict() if "district" in self.df.columns else {}
        wards = self.df["ward"].value_counts().head(top_n).to_dict() if "ward" in self.df.columns else {}
        
        logger.info(f"Location Analysis complete (Top {top_n} profiles).")
        return {
            "top_locations": {str(k): int(v) for k, v in loc_desc.items()},
            "top_districts": {str(k): int(v) for k, v in districts.items()},
            "top_wards": {str(k): int(v) for k, v in wards.items()}
        }

    def run_statistical_summaries(self) -> Dict[str, Any]:
        """
        Calculates arrest rates, domestic incidents, and cross-tabulations.
        """
        total = len(self.df)
        if total == 0:
            return {"arrest_rate": 0.0, "domestic_rate": 0.0}
            
        arrests = int(self.df["arrest"].sum()) if "arrest" in self.df.columns else 0
        domestic = int(self.df["domestic"].sum()) if "domestic" in self.df.columns else 0
        
        # Arrest rate by category
        arrest_by_cat = {}
        if "arrest" in self.df.columns and "category" in self.df.columns:
            grouped = self.df.groupby("category")
            for cat, group in grouped:
                cat_total = len(group)
                cat_arrests = int(group["arrest"].sum())
                arrest_by_cat[str(cat)] = {
                    "total": cat_total,
                    "arrests": cat_arrests,
                    "arrest_rate": round(float((cat_arrests / cat_total) * 100), 2) if cat_total > 0 else 0.0
                }

        # Day-of-week vs. Hour-of-day matrix counts (for heatmap)
        dow_hour_matrix = np.zeros((7, 24), dtype=int)
        for (hour, dow), count in self.df.groupby(["hour", "day_of_week"]).size().items():
            dow_hour_matrix[int(dow), int(hour)] = int(count)
            
        # Convert matrix to a list of lists for JSON serializability
        matrix_list = dow_hour_matrix.tolist()

        logger.info("Statistical Summaries complete.")
        return {
            "overall_arrest_rate": round(float((arrests / total) * 100), 2),
            "overall_domestic_rate": round(float((domestic / total) * 100), 2),
            "arrest_rates_by_category": arrest_by_cat,
            "day_hour_density_matrix": matrix_list
        }

    def generate_all_reports(self) -> Dict[str, Any]:
        """
        Aggregates all analysis modules into a single report dictionary.
        """
        logger.info("Generating full analytical profile...")
        return {
            "frequency": self.run_frequency_analysis(),
            "categories": self.run_category_analysis(),
            "temporal": self.run_temporal_analysis(),
            "locations": self.run_location_analysis(),
            "statistics": self.run_statistical_summaries()
        }
