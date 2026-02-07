"""
Data Catalog for CRM Service Request Analytics
Describes all available data products and their purposes
"""

DATA_CATALOG = {
    "top10_volume_30d": {
        "file": "top10.csv",
        "description": "Top 10 service categories by volume in the last 30 days",
        "filter": "ranking_type == 'Volume (Last 30 Days)'",
        "use_cases": ["identify highest demand", "prioritize resources", "current trends"],
        "metrics": ["volume", "percentage of total"]
    },
    "top10_worst_p90_time": {
        "file": "top10.csv",
        "description": "Top 10 categories with worst P90 time-to-close performance",
        "filter": "ranking_type == 'Worst P90 Time-to-Close'",
        "use_cases": ["identify bottlenecks", "SLA violations", "performance issues"],
        "metrics": ["p90_days", "median_days", "request_count"]
    },
    "top10_backlog_age": {
        "file": "top10.csv",
        "description": "Top 10 categories with oldest backlog (by P90 age)",
        "filter": "ranking_type == 'Backlog Age'",
        "use_cases": ["identify aging backlogs", "urgent old items", "overdue requests"],
        "metrics": ["p90_age_days", "avg_age_days", "open_count"]
    },
    "top10_trending_up": {
        "file": "top10.csv",
        "description": "Top 10 categories trending upward in volume",
        "filter": "ranking_type == 'Trending Up'",
        "use_cases": ["emerging issues", "growing demand", "proactive planning"],
        "metrics": ["absolute_change", "growth_rate", "recent_volume"]
    },
    "top10_geographic_hotspots": {
        "file": "top10.csv",
        "description": "Top 10 geographic areas by service request volume",
        "filter": "ranking_type == 'Geographic Hotspots'",
        "use_cases": ["area-specific issues", "resource deployment", "geographic priorities"],
        "metrics": ["volume", "pct_of_total", "top_category"]
    },
    "frequency_over_time": {
        "file": "frequency_over_time.csv",
        "description": "Monthly time series of service request volume by category from 2019-present",
        "filter": None,
        "use_cases": ["identify trends", "seasonal patterns", "growth analysis", "forecasting"],
        "metrics": ["monthly counts per category"]
    },
    "backlog_ranked_list": {
        "file": "backlog_ranked_list.csv",
        "description": "Unresolved service requests ranked by count and average age",
        "filter": None,
        "use_cases": ["identify aging issues", "urgent unresolved items", "backlog management"],
        "metrics": ["unresolved_count", "avg_age_days"]
    },
    "backlog_distribution": {
        "file": "backlog_distribution.csv",
        "description": "Distribution of open backlogs across service categories",
        "filter": None,
        "use_cases": ["backlog overview", "resource allocation", "workload distribution"],
        "metrics": ["open_count", "percentage"]
    },
    "time_to_close": {
        "file": "time_to_close.csv",
        "description": "Time-to-close statistics by category with distribution bins",
        "filter": None,
        "use_cases": ["performance analysis", "SLA tracking", "efficiency metrics"],
        "metrics": ["median", "p75", "p90", "mean", "min", "max"]
    },
    "geographic_hot_spots": {
        "file": "geographic_hot_spots.csv",
        "description": "Geographic clustering of service requests by ward/area",
        "filter": None,
        "use_cases": ["spatial analysis", "resource deployment", "area-specific issues"],
        "metrics": ["request_count", "geographic coordinates"]
    },
    "seasonality_heatmap": {
        "file": "seasonality_heatmap.csv",
        "description": "Day-of-week and month patterns for service requests",
        "filter": None,
        "use_cases": ["seasonal patterns", "staffing planning", "cyclical trends"],
        "metrics": ["request counts by time periods"]
    },
    "fcr_by_category": {
        "file": "fcr_by_category.csv",
        "description": "First Call Resolution rates by service category",
        "filter": None,
        "use_cases": ["quality metrics", "efficiency analysis", "customer satisfaction"],
        "metrics": ["FCR rate", "resolution metrics"]
    },
    "priority_quadrant": {
        "file": "priority_quadrant_data_p90.csv",
        "description": "Priority matrix combining volume and time-to-close (P90)",
        "filter": None,
        "use_cases": ["prioritization", "strategic planning", "resource optimization"],
        "metrics": ["volume", "p90_days", "quadrant assignment"]
    }
}


def get_catalog_summary() -> str:
    """Generate a human-readable summary of the data catalog"""
    summary = "## Available Data Products\n\n"
    
    for product_id, details in DATA_CATALOG.items():
        summary += f"**{product_id}**\n"
        summary += f"- Description: {details['description']}\n"
        summary += f"- Use Cases: {', '.join(details['use_cases'])}\n"
        summary += f"- Key Metrics: {', '.join(details['metrics'])}\n\n"
    
    return summary


def get_product_details(product_id: str) -> dict:
    """Get details for a specific data product"""
    return DATA_CATALOG.get(product_id, None)
