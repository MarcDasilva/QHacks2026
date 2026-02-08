# Dual-Mode Chat System - Feature Documentation

## Overview
The chat system now supports **two modes** based on user intent:
1. **Simple Chat Mode** - Quick conversational responses without data analysis
2. **Deep Analysis Mode** - Full two-stage analysis with data visualization and navigation

## How It Works

### 🔍 Keyword Detection
The system automatically detects the word **"analysis"** in user messages:
- **"analysis" present** → Shows confirmation dialog
- **"analysis" absent** → Goes straight to simple chat mode

### 💬 User Flow

#### Scenario 1: Simple Chat (No "analysis" keyword)
```
User: "What are service requests?"
  ↓
System: [Simple Chat Mode]
  ↓
Gemini provides conversational response
```

**Example:**
- User: "What are service requests?"
- Bot: "Service requests are submissions by citizens to report issues like potholes, broken streetlights, or request municipal services..."

#### Scenario 2: Deep Analysis Request
```
User: "Show me an analysis of top categories"
  ↓
System: Detects "analysis" keyword
  ↓
Shows confirmation dialog:
  🔍 "Would you like to perform a deep analysis with data visualization?"
  [Yes, Deep Analysis] [No, Simple Chat]
  ↓
User selects their preference
  ↓
Executes chosen mode
```

**If YES (Deep Analysis):**
- 🤔 Planning stage (selects data products)
- 📊 Data loading
- 🧭 Auto-navigation to relevant pages
- 📈 Final analysis with metrics

**If NO (Simple Chat):**
- 💬 Quick conversational response
- No data loading or navigation

## Backend Changes

### New Method: `simple_chat()` in GeminiAgent
```python
def simple_chat(self, user_question: str) -> str:
    """
    Direct conversation with Gemini - no data retrieval
    Provides context about being the Mayor's assistant
    """
```

### Updated Endpoint: `/api/chat/stream`
Now accepts `mode` parameter:
```json
{
  "message": "user question",
  "mode": "auto"  // "auto", "deep_analysis", or "chat"
}
```

**Mode behavior:**
- `"auto"` - Checks for "analysis" keyword automatically
- `"deep_analysis"` - Forces deep analysis mode
- `"chat"` - Forces simple chat mode

### Two Stream Functions
1. **`stream_simple_chat()`** - For chat mode
2. **`stream_agent_response()`** - For deep analysis mode

## Frontend Changes

### New Message Types
- **`"chat"`** - Simple conversational responses
- **`"confirmation"`** - Yes/No dialog for analysis confirmation

### New State
- `pendingMessage` - Stores message waiting for user's mode selection

### Flow Control
```typescript
handleSubmit()
  ↓ (checks for "analysis")
  ↓
showConfirmation() OR sendMessage("chat")
  ↓
handleConfirmation(true/false)
  ↓
sendMessage(mode)
```

## Example Interactions

### Example 1: Simple Chat
```
👤 User: "What types of requests do cities handle?"

🤖 Bot: Cities typically handle various types of requests including:
- Infrastructure maintenance (roads, sidewalks, traffic lights)
- Parks and recreation services
- Waste management
- Public safety concerns
- Building permits and inspections
...
```

### Example 2: Analysis Detection
```
👤 User: "Can you do an analysis of the most common requests?"

🔍 Bot: Would you like to perform a deep analysis with data visualization?
     [Yes, Deep Analysis] [No, Simple Chat]

(If user clicks "Yes, Deep Analysis")
🤔 Bot: Analyzing your question and planning...
📋 Plan: Selected top10_volume_30d
📊 Loading data...
🧭 Navigating to analytics view
🧠 Analyzing data...
📊 Analysis Complete: Recreation and leisure has 663 requests (18.5%)...

(If user clicks "No, Simple Chat")
💬 Bot: Based on typical municipal data, the most common requests 
     usually include road maintenance, traffic issues, and parks...
```

### Example 3: Multiple "analysis" Keywords
```
👤 User: "I need an analysis of trends over time for my analysis report"

🔍 Bot: Would you like to perform a deep analysis with data visualization?
     (Confirmation shown because "analysis" appears in the message)
```

## Removing the Default Fallback

### ❌ Removed
- Default fallback in `plan_stage()` that returned generic data products on JSON parse error
- System no longer assumes user wants any specific data

### ✅ Replaced With
- Explicit mode selection via confirmation dialog
- Clear user choice between analysis and chat
- Better error handling with descriptive messages

## Configuration

### Backend Context (Simple Chat)
Located in `gemini_client.py`:
```python
prompt = """You are an intelligent assistant to the Mayor, 
specializing in municipal service requests and CRM data.

You have knowledge about:
- Municipal service request categories
- Service request lifecycle
- Common municipal operations
..."""
```

**To customize:** Edit the prompt in `GeminiAgent.simple_chat()` method

### Frontend Confirmation Text
Located in `chat-interface.tsx`:
```typescript
content: "Would you like to perform a deep analysis with data visualization?"
```

**To customize:** Change the confirmation message content

## Testing

### Test Simple Chat
```
Message: "What are service requests?"
Expected: Immediate conversational response, no confirmation dialog
```

### Test Analysis Detection
```
Message: "Show me an analysis of trends"
Expected: Confirmation dialog appears with Yes/No buttons
```

### Test Deep Analysis (Yes)
```
1. Send: "Give me an analysis of top categories"
2. Click: "Yes, Deep Analysis"
Expected: Full pipeline with planning, data loading, navigation, and analysis
```

### Test Simple Chat from Analysis (No)
```
1. Send: "Give me an analysis of top categories"
2. Click: "No, Simple Chat"
Expected: Quick conversational response about categories
```

## Troubleshooting

### Confirmation doesn't appear
- Check: Message contains "analysis" (case-insensitive)
- Verify: Frontend console for errors

### Both buttons don't work
- Check: `isLoading` state not stuck
- Verify: `pendingMessage` is set correctly

### Simple chat returns errors
- Check: `GEMINI_API_KEY` is valid
- Verify: Backend console shows Gemini response

### Deep analysis fails after clicking "Yes"
- Check: All original data products are available
- Verify: Backend agent is initialized properly

## API Examples

### Force Simple Chat Mode
```bash
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "mode": "chat"}'
```

### Force Deep Analysis Mode
```bash
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Show trends", "mode": "deep_analysis"}'
```

### Auto-detect Mode
```bash
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Analysis of data", "mode": "auto"}'
```

## Benefits

✅ **User Control** - Users explicitly choose their intent
✅ **Better UX** - No unnecessary data loading for simple questions
✅ **Faster Responses** - Simple chat is much quicker
✅ **Clear Intent** - System knows exactly what user wants
✅ **Flexible** - Can force either mode via API
✅ **Resource Efficient** - Only loads data when needed

---

**Note:** Restart the backend server after making these changes for them to take effect!
