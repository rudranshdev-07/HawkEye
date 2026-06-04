import os
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from typing import Dict, Any
from src.utils.logging_config import logger

def set_style():
    """
    Applies custom premium Seaborn theme settings.
    """
    sns.set_theme(style="darkgrid", context="talk")
    plt.rcParams.update({
        "figure.facecolor": "#121214",
        "axes.facecolor": "#1a1a1e",
        "axes.edgecolor": "#2a2a30",
        "text.color": "#e1e1e6",
        "axes.labelcolor": "#a9a9b3",
        "xtick.color": "#a9a9b3",
        "ytick.color": "#a9a9b3",
        "font.family": "sans-serif",
        "grid.color": "#2a2a30",
        "grid.linestyle": "--",
        "grid.linewidth": 0.5
    })

def generate_and_save_charts(report: Dict[str, Any], output_dir: str = "reports/charts") -> None:
    """
    Generates all analytical visualizations and saves them as high-quality PNGs.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created directory for charts: {output_dir}")

    # Set premium style
    set_style()
    
    # 1. Category Distribution Chart
    try:
        categories = report["categories"]
        cats = sorted(categories.keys(), key=lambda x: categories[x]["count"], reverse=True)
        counts = [categories[c]["count"] for c in cats]
        
        plt.figure(figsize=(12, 7))
        # Use a premium gradient color palette
        colors = sns.color_palette("flare", len(cats))
        sns.barplot(x=counts, y=cats, hue=cats, palette=colors, legend=False)
        plt.title("Crime Volume by Category", fontsize=18, fontweight="bold", pad=20, color="#ffffff")
        plt.xlabel("Number of Incidents", labelpad=12)
        plt.ylabel("Category", labelpad=12)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "category_distribution.png"), dpi=150, facecolor="#121214")
        plt.close()
        logger.info("Category distribution chart saved.")
    except Exception as e:
        logger.error(f"Failed to generate category distribution chart: {str(e)}")

    # 2. Hourly Crime Distribution (Diurnal Curve)
    try:
        hourly = report["temporal"]["hourly_distribution"]
        hours = list(range(24))
        counts = [hourly.get(h, hourly.get(str(h), 0)) for h in hours]
        
        plt.figure(figsize=(12, 6))
        # Draw a smooth line and fill underneath
        plt.plot(hours, counts, color="#00ffb7", linewidth=3, marker="o", markersize=6)
        plt.fill_between(hours, counts, color="#00ffb7", alpha=0.15)
        
        plt.title("Hourly Crime Distribution", fontsize=18, fontweight="bold", pad=20, color="#ffffff")
        plt.xlabel("Hour of Day (24h)", labelpad=12)
        plt.ylabel("Crime Count", labelpad=12)
        plt.xticks(hours)
        plt.xlim(0, 23)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "hourly_distribution.png"), dpi=150, facecolor="#121214")
        plt.close()
        logger.info("Hourly distribution chart saved.")
    except Exception as e:
        logger.error(f"Failed to generate hourly distribution chart: {str(e)}")

    # 3. Weekly Crime Distribution
    try:
        weekly = report["temporal"]["weekly_distribution"]
        days = list(weekly.keys())
        counts = list(weekly.values())
        
        plt.figure(figsize=(10, 6))
        colors = sns.color_palette("viridis", len(days))
        sns.barplot(x=days, y=counts, hue=days, palette=colors, legend=False)
        plt.title("Crime Frequency by Day of Week", fontsize=18, fontweight="bold", pad=20, color="#ffffff")
        plt.xlabel("Day of Week", labelpad=12)
        plt.ylabel("Crime Count", labelpad=12)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "weekly_distribution.png"), dpi=150, facecolor="#121214")
        plt.close()
        logger.info("Weekly distribution chart saved.")
    except Exception as e:
        logger.error(f"Failed to generate weekly distribution chart: {str(e)}")

    # 4. Monthly Crime Seasonality
    try:
        monthly = report["temporal"]["monthly_seasonality"]
        months = list(monthly.keys())
        counts = list(monthly.values())
        
        plt.figure(figsize=(12, 6))
        plt.plot(months, counts, color="#ff007f", linewidth=3, marker="s", markersize=8)
        plt.fill_between(months, counts, color="#ff007f", alpha=0.1)
        plt.title("Monthly Crime Seasonality", fontsize=18, fontweight="bold", pad=20, color="#ffffff")
        plt.xlabel("Month", labelpad=12)
        plt.ylabel("Crime Count", labelpad=12)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "monthly_seasonality.png"), dpi=150, facecolor="#121214")
        plt.close()
        logger.info("Monthly seasonality chart saved.")
    except Exception as e:
        logger.error(f"Failed to generate monthly seasonality chart: {str(e)}")

    # 5. Day-of-Week vs. Hour-of-Day Crime Density Heatmap
    try:
        matrix = report["statistics"]["day_hour_density_matrix"]
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        hours = [f"{h:02d}h" for h in range(24)]
        
        plt.figure(figsize=(14, 8))
        # Custom dark palette heatmap
        sns.heatmap(
            matrix, 
            xticklabels=hours, 
            yticklabels=days, 
            cmap="mako", 
            cbar_kws={"label": "Crime Count"},
            linewidths=0.5,
            linecolor="#1a1a1e"
        )
        plt.title("Crime Density by Day & Hour", fontsize=18, fontweight="bold", pad=20, color="#ffffff")
        plt.xlabel("Hour of Day", labelpad=12)
        plt.ylabel("Day of Week", labelpad=12)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "crime_density_heatmap.png"), dpi=150, facecolor="#121214")
        plt.close()
        logger.info("Crime density heatmap saved.")
    except Exception as e:
        logger.error(f"Failed to generate crime density heatmap: {str(e)}")
        
    logger.info("All analytical charts generated successfully.")
