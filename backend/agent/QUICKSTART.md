# 🤖 CRM Analytics Agent - Quick Start Guide

## 🎯 Overview

The CRM Analytics Agent uses **Gemini AI** with a **two-stage prompting architecture**:

1. **Planning Stage** (Prompt 1): Gemini decides which data products to use based on the user's question
2. **Analysis Stage** (Prompt 2): Gemini generates a detailed answer using the fetched data

## 📁 Architecture

```
User Question
     ↓
┌─────────────────────────────────┐
│  Stage 1: Planning (Gemini)    │
│  Input:                         │
│  - User question                │
│  - Data catalog                 │
│  - frequency_over_time.csv preview │
│                                 │
│  Output: JSON array             │
│  [                              │
│    {                            │
│      "product": "top10_volume_30d",│
│      "why": "Identify demand"   │
│    }                            │
│  ]                              │
└─────────────────────────────────┘
     ↓
┌─────────────────────────────────┐
│  Data Fetching                  │
│  Loads CSVs from                │
│  backend/trends/data/           │
└─────────────────────────────────┘
     ↓
┌─────────────────────────────────┐
│  Stage 2: Analysis (Gemini)    │
│  Input:                         │
│  - User question                │
│  - Access log (plan)            │
│  - Fetched data summaries       │
│                                 │
│  Output: JSON response          │
│  {                              │
│    "answer": "...",             │
│    "rationale": [...],          │
│    "key_metrics": [...]         │
│  }                              │
└─────────────────────────────────┘
     ↓
Final Structured Answer
```

## 🚀 Quick Start

### 1. Install Dependencies

```powershell
cd backend
pip install -r requirements.txt
```

### 2. Set API Key

Get a free Gemini API key: https://makersuite.google.com/app/apikey

```powershell
# PowerShell
$env:GEMINI_API_KEY="your-api-key-here"
```

### 3. Run Example

```powershell
cd backend/agent
python example.py
```

## 💻 Usage Examples

### Python Script Usage

```python
from backend.agent import CRMAnalyticsAgent

# Initialize
agent = CRMAnalyticsAgent()

# Ask a question
result = agent.query("What are the top service categories by volume?")

# Access results
print(result["answer"])         # Main answer
print(result["rationale"])      # Detailed points
print(result["key_metrics"])    # Referenced numbers
print(result["plan"])           # Which data was used
```

### FastAPI Integration

```python
# Run the API server
cd backend/agent
python api_integration.py

# Or with uvicorn
uvicorn api_integration:app --reload
```

Then query via HTTP:

```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the top categories?", "verbose": false}'
```

### Response Format

```json
{
  "question": "What are the top service categories by volume?",
  "plan": [
    {
      "product": "top10_volume_30d",
      "why": "Identify highest current demand"
    }
  ],
  "fetched_products": ["top10_volume_30d"],
  "answer": "Recreation and leisure has the highest volume with 663 requests (18.5%) in the last 30 days, followed by Roads, traffic and sidewalks with 562 requests (15.68%).",
  "rationale": [
    "Recreation and leisure leads with 663 requests (18.5% of total volume)",
    "Roads, traffic and sidewalks is second with 562 requests (15.68%)",
    "These top 2 categories account for 34.18% of all recent requests"
  ],
  "key_metrics": ["663 requests", "18.5%", "562 requests", "15.68%"]
}
```

## 📊 Available Data Products

The agent automatically selects from these data sources:

| Product ID | Description | Use Cases |
|------------|-------------|-----------|
| `top10_volume_30d` | Top 10 by recent volume | Current demand, priorities |
| `top10_worst_p90_time` | Worst P90 time-to-close | Bottlenecks, SLA issues |
| `top10_backlog_age` | Top 10 oldest backlogs | Aging issues, overdue items |
| `top10_trending_up` | Top 10 trending upward | Emerging issues, growth |
| `top10_geographic_hotspots` | Top 10 geographic areas | Spatial analysis, deployment |
| `frequency_over_time` | Monthly time series | Trends, seasonality |
| `backlog_ranked_list` | Unresolved by age | Aging issues, urgent items |
| `backlog_distribution` | Open backlog overview | Resource allocation |
| `time_to_close` | Resolution statistics | Performance, efficiency |
| `geographic_hot_spots` | Geographic clusters | Spatial analysis |
| `seasonality_heatmap` | Day/month patterns | Staffing planning |
| `fcr_by_category` | First Call Resolution | Quality metrics |
| `priority_quadrant` | Volume × Time matrix | Strategic planning |

## 🎯 Example Questions

Try these questions with the agent:

**Volume & Demand:**
- "What are the top 5 service categories by volume in the last 30 days?"
- "Which categories have seen increasing request volumes over time?"

**Performance:**
- "Which service categories have the worst response times?"
- "Show me P90 time-to-close for all categories"

**Backlog:**
- "What unresolved issues are older than 1000 days?"
- "Which categories have the largest backlogs?"
- "Show me the top 10 categories with the oldest backlog"

**Trends:**
- "What are the seasonal trends for garbage and recycling?"
- "Show me request patterns by month and day of week"
- "Which categories are trending upward the most?"

**Geographic:**
- "Which areas have the most service requests?"
- "Where are the geographic hot spots?"
- "What are the top 10 neighborhoods by request volume?"

**Strategic:**
- "What should we prioritize based on volume and resolution time?"
- "Which categories need the most attention?"

## 🔧 Advanced Usage

### Custom Data Directory

```python
agent = CRMAnalyticsAgent(
    data_dir="/path/to/custom/data"
)
```

### Batch Processing

```python
questions = [
    "What are the top categories?",
    "Which have worst response times?",
    "Show me the backlog"
]

results = agent.batch_query(questions)
```

### Silent Mode (No Console Output)

```python
result = agent.query("Your question here", verbose=False)
```

## 🌐 API Endpoints

When running the FastAPI server:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/api/query` | POST | Single question |
| `/api/batch-query` | POST | Multiple questions |
| `/api/catalog` | GET | View data catalog |
| `/api/catalog/{id}` | GET | Product details |

## 📝 Files in backend/agent/

- **`agent.py`** - Main CRMAnalyticsAgent orchestrator
- **`gemini_client.py`** - Two-stage Gemini prompting logic
- **`catalog.py`** - Data product catalog
- **`data_loader.py`** - CSV loading utilities
- **`api_integration.py`** - FastAPI REST API
- **`example.py`** - Example usage script
- **`README.md`** - Detailed documentation

## 🔐 Environment Variables

Create `.env` file:

```bash
GEMINI_API_KEY=your-api-key-here
```

Load in Python:

```python
from dotenv import load_dotenv
load_dotenv()
```

## 🐛 Troubleshooting

**"API key not set" error:**
```powershell
$env:GEMINI_API_KEY="your-key"
# Verify
echo $env:GEMINI_API_KEY
```

**Import errors:**
```powershell
# Make sure you're in the right directory
cd backend
python -m agent.example
```

**Data not found:**
- Ensure CSV files exist in `backend/trends/data/`
- Check file permissions

## 🚀 Next Steps

1. **Test the example:** Run `python example.py`
2. **Try custom questions:** Modify the example script
3. **Integrate with frontend:** Use the FastAPI endpoints
4. **Customize catalog:** Add new data products in `catalog.py`
5. **Tune prompts:** Adjust prompts in `gemini_client.py`

## 💡 Tips

- The agent selects 2-4 data products per query automatically
- Include specific keywords to guide data selection
- Ask follow-up questions to dive deeper
- Use batch mode for related questions
- Check `result["plan"]` to see which data was used

Happy analyzing! 🎉
