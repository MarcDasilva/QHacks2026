# CRM Analytics Agent

A two-stage Gemini-powered agent for intelligent CRM service request analysis.

## Overview

This agent uses a two-prompt architecture:

1. **Planning Stage**: Gemini analyzes the user's question and determines which data products to fetch
2. **Analysis Stage**: Gemini generates a final answer using the retrieved data

## Architecture

```
User Question
     ↓
[Stage 1: Planning]
  - Input: Question + Data Catalog + Sample Data
  - Output: List of data products to fetch
     ↓
[Data Fetching]
  - Loads specified CSV files from backend/trends/data
  - Converts to summaries for LLM consumption
     ↓
[Stage 2: Analysis]
  - Input: Question + Access Log + Fetched Data
  - Output: Final answer with rationale and metrics
     ↓
Structured Response
```

## Files

- `agent.py` - Main orchestrator (CRMAnalyticsAgent class)
- `gemini_client.py` - Gemini API integration with two-stage prompting
- `catalog.py` - Data product catalog and descriptions
- `data_loader.py` - CSV loading and data summarization utilities
- `__init__.py` - Package initialization

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your Gemini API key in `backend/.env`:
```bash
# Edit backend/.env file
GEMINI_API_KEY=your-api-key-here
```

Note: The agent automatically loads environment variables from `backend/.env`

## Usage

### Basic Usage

```python
from backend.agent import CRMAnalyticsAgent

# Initialize the agent
agent = CRMAnalyticsAgent()

# Ask a question
result = agent.query("What are the top service categories by volume?")

# Access the response
print(result["answer"])
print(result["rationale"])
print(result["key_metrics"])
```

### Response Format

```python
{
    "question": "Original user question",
    "plan": [
        {
            "product": "top10_volume_30d",
            "why": "Identify highest current demand"
        }
    ],
    "fetched_products": ["top10_volume_30d", "backlog_ranked_list"],
    "answer": "Concise answer to the question",
    "rationale": [
        "Detailed point 1 with numbers",
        "Detailed point 2 with numbers", 
        ...
    ],
    "key_metrics": ["663 requests", "18.5%", ...]
}
```

### Batch Processing

```python
questions = [
    "What are the top categories by volume?",
    "Which categories have the worst response times?",
    "What are the seasonal trends?"
]

results = agent.batch_query(questions)
```

### Command Line Usage

```bash
cd backend/agent
python agent.py
```

## Available Data Products

The agent can access these data products:

- **top10_volume_30d** - Top categories by recent volume
- **top10_worst_p90_time** - Categories with worst P90 time-to-close
- **top10_backlog_age** ⭐ - Top 10 oldest backlogs by P90 age
- **top10_trending_up** ⭐ - Top 10 categories trending upward  
- **top10_geographic_hotspots** ⭐ - Top 10 geographic areas by volume
- **frequency_over_time** - Monthly time series by category
- **backlog_ranked_list** - Unresolved requests by age
- **backlog_distribution** - Open backlog distribution
- **time_to_close** - Time-to-close statistics
- **geographic_hot_spots** - Geographic clustering
- **seasonality_heatmap** - Day/month patterns
- **fcr_by_category** - First Call Resolution rates
- **priority_quadrant** - Priority matrix (volume × time)

## Example Questions

- "What are the top 5 service categories by volume in the last 30 days?"
- "Which categories have the longest resolution times?"
- "Show me the backlog of unresolved issues older than 1000 days"
- "What are the seasonal trends for garbage and recycling requests?"
- "Which categories have the oldest backlogs?" ⭐
- "What are the seasonal trends for garbage and recycling requests?"
- "Which areas have the most service requests?"
- "What's the priority quadrant for resource allocation?"
- "Which categories are trending upward the most?" ⭐
- "What are the top geographic hotspots?" ⭐
## Integration with FastAPI

```python
from fastapi import FastAPI
from backend.agent import CRMAnalyticsAgent

app = FastAPI()
agent = CRMAnalyticsAgent()

@app.post("/api/query")
async def query_crm_data(question: str):
    result = agent.query(question, verbose=False)
    return result
```

## Notes

- The agent automatically selects 1-3 relevant data products per query
- Data is loaded from `backend/trends/data/` folder
- Responses include specific numbers and references from the data
- Set `verbose=True` for detailed console output during processing
- The planning stage reduces token usage by only fetching relevant data
