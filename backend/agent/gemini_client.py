"""
Gemini AI client for the two-stage prompting system
"""

import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
from google import genai


def _log_prompt_to_console(method: str, prompt: str) -> None:
    """Log the prompt sent to Gemini to the console for debugging."""
    print(f"\n[Gemini prompt] method={method} len={len(prompt)}")
    print("-" * 60)
    print(prompt)
    print("-" * 60)

# Load environment variables from backend/.env
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)


class GeminiAgent:
    """
    Two-stage Gemini agent for CRM analytics
    Stage 1: Planning - determines which data products to use
    Stage 2: Analysis - provides final answer based on retrieved data
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client
        
        Args:
            api_key: Google AI API key. If None, reads from GEMINI_API_KEY env var
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key must be provided or set in GEMINI_API_KEY environment variable")
        
        self.client = genai.Client()
    
    def plan_stage(
        self, 
        user_question: str, 
        catalog_summary: str,
        frequency_data_preview: str
    ) -> List[Dict[str, str]]:
        """
        Stage 1: Planning prompt to determine which data products to use
        
        Args:
            user_question: The user's original question
            catalog_summary: Summary of available data products
            frequency_data_preview: Preview of frequency_over_time.csv
            
        Returns:
            List of dictionaries with 'product' and 'why' keys
        """
        
        prompt = f"""You are a data analyst planning how to answer a user's question about CRM service requests.

USER QUESTION:
{user_question}

AVAILABLE DATA PRODUCTS:
{catalog_summary}

SAMPLE DATA (frequency_over_time.csv preview):
{frequency_data_preview}

Your task is to determine which data products would be most helpful to answer the user's question.

IMPORTANT: Return ONLY a valid JSON array with no additional text, markdown formatting, or code blocks. The response must be parseable JSON.

Output format (JSON array only):
[
  {{
    "product": "product_id_from_catalog",
    "why": "Brief reason why this data is needed"
  }},
  {{
    "product": "another_product_id",
    "why": "Another brief reason"
  }}
]

Select 1-3 most relevant data products. Be strategic - choose products that directly answer the question.
Keep each "why" to one short phrase (under 10 words).
Return only the JSON array, nothing else."""

        _log_prompt_to_console("plan_stage", prompt)
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                # Extract content between code blocks
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
                if response_text.startswith("json"):
                    response_text = response_text[4:].strip()
            
            # Parse JSON response
            plan = json.loads(response_text)
            return plan
        
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Raw response: {response.text}")
            # Return a default fallback
            return [
                {"product": "top10_volume_30d", "why": "Identify highest current demand"},
                {"product": "backlog_ranked_list", "why": "Identify urgent unresolved items"}
            ]
        except Exception as e:
            print(f"Error in plan stage: {e}")
            raise
    
    def analysis_stage(
        self,
        user_question: str,
        access_log: List[Dict[str, str]],
        fetched_data: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Stage 2: Analysis prompt to provide final answer with data
        
        Args:
            user_question: The user's original question
            access_log: The plan from stage 1 (list of products accessed)
            fetched_data: Dictionary mapping product_id to data summary string
            
        Returns:
            Dictionary with 'answer' and 'rationale' keys
        """
        
        # Format the fetched data section
        data_section = ""
        for product_id, data_summary in fetched_data.items():
            data_section += f"\n### Data Product: {product_id}\n"
            data_section += f"{data_summary}\n"
            data_section += "-" * 80 + "\n"
        
        # Format access log
        access_log_str = json.dumps(access_log, indent=2)
        
        prompt = f"""You are a data analyst providing insights on CRM service request data.

USER QUESTION:
{user_question}

DATA PRODUCTS ACCESSED:
{access_log_str}

RETRIEVED DATA:
{data_section}

Based on the data provided above, answer the user's question as briefly as possible.

Format your response as a JSON object with these keys:
- "answer": One or two short sentences max. Be as short as possible.
- "rationale": 1-3 brief bullet points with key numbers only.
- "key_metrics": Short list of numbers referenced (e.g., ["663", "18.5%"]).

IMPORTANT: Keep every part minimal. Return ONLY valid JSON with no additional text, markdown, or code blocks.

Example format:
{{
  "answer": "Recreation leads with 663 requests (18.5%). Roads/traffic second at 562 (15.7%).",
  "rationale": ["Recreation 663 (18.5%)", "Roads 562 (15.7%)"],
  "key_metrics": ["663", "18.5%", "562", "15.7%"]
}}

Now analyze the data and respond (keep it short):"""

        _log_prompt_to_console("analysis_stage", prompt)
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt)
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
                if response_text.startswith("json"):
                    response_text = response_text[4:].strip()
            
            # Parse JSON response
            result = json.loads(response_text)
            return result
        
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Raw response: {response.text}")
            # Return the raw text as answer if JSON parsing fails
            return {
                "answer": response.text,
                "rationale": ["Unable to parse structured response"],
                "key_metrics": []
            }
        except Exception as e:
            print(f"Error in analysis stage: {e}")
            raise
    
    def extract_search_keywords(self, user_message: str, context: str = "") -> str:
        """
        Extract search keywords from the user message for cluster embedding search.
        Use before predict_cluster so the embedding query aligns with cluster labels.
        
        Args:
            user_message: The user's raw message (e.g. "Im interested in people booking city hall")
            context: Optional context (e.g. "matching against Facility Booking, City Hall Room Booking")
            
        Returns:
            Short phrase (5–15 words) optimized for semantic search against cluster labels
        """
        prompt = f"""You are helping prepare a search query for matching a user message against municipal service request cluster labels (e.g. "Facility Booking", "City Hall Room Booking", "Parks", "Roads").

User message: {user_message}
{f"Context: {context}" if context.strip() else ""}

Output a single short phrase (5–15 words) that captures the key concepts for semantic search. Use terms that would match cluster labels: facility, booking, city hall, room, parks, roads, complaints, reservations, etc. No quotes or explanation—only the search phrase."""

        _log_prompt_to_console("extract_search_keywords", prompt)
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            text = response.text.strip().strip('"\'')
            return text if text else user_message[:200]
        except Exception as e:
            print(f"Error in extract_search_keywords: {e}")
            return user_message[:200]

    def plan_one_analytics_product_for_cluster(
        self,
        parent_label: str,
        child_label: str,
        catalog_summary: str,
        frequency_preview: str,
    ) -> List[Dict[str, str]]:
        """
        Plan which single data product (that has an analytics page) is most relevant
        for a cluster the user is viewing. Returns a list with one item for compatibility with plan_stage.
        """
        prompt = f"""You are a data analyst. The user is viewing a cluster: "{parent_label}" (sub-cluster: "{child_label}").

Choose the SINGLE most relevant data product to show on an analytics dashboard for this cluster.

AVAILABLE DATA PRODUCTS (only these have dashboard pages):
{catalog_summary}

SAMPLE DATA (frequency_over_time preview):
{frequency_preview}

IMPORTANT: Return ONLY a valid JSON array with exactly ONE object. No other text.
Output format: [{{ "product": "product_id_from_catalog", "why": "Brief reason" }}]

Pick ONE product that best fits this cluster. Valid product IDs include: frequency_over_time, backlog_ranked_list, backlog_distribution, priority_quadrant, geographic_hot_spots, time_to_close.
Return only the JSON array."""

        _log_prompt_to_console("plan_one_analytics_product_for_cluster", prompt)
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            text = response.text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
                if text.startswith("json"):
                    text = text[4:].strip()
            plan = json.loads(text)
            return plan if isinstance(plan, list) else [plan]
        except Exception as e:
            print(f"Error in plan_one_analytics_product_for_cluster: {e}")
            return [{"product": "frequency_over_time", "why": "Default trend view"}]

    def discuss_analytics_visit(
        self,
        parent_label: str,
        child_label: str,
        product_id: str,
        product_display_name: str,
        data_summary: str,
    ) -> str:
        """
        Generate 1-3 sentences discussing how this analytics view relates to the cluster
        or general trends when the relationship is weak.
        """
        prompt = f"""You are an assistant to the Mayor. The user just opened the "{product_display_name}" analytics view after viewing the cluster "{parent_label}" (sub-cluster "{child_label}").

Data summary for this view (brief):
{data_summary[:2000] if data_summary else "No summary available."}

Write 1-3 short sentences that either:
- Explain how this analytics view relates to that cluster (if there is a clear link), or
- Discuss general trends from the data (if the link is weak).

Be concise and natural. No bullet points. Output only the paragraph."""

        _log_prompt_to_console("discuss_analytics_visit", prompt)
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"Error in discuss_analytics_visit: {e}")
            return f"This {product_display_name} view shows trends that can complement the \"{parent_label}\" cluster you were viewing."

    def report_data_from_discussion(
        self,
        parent_label: str,
        child_label: str,
        discussion: str,
    ) -> Dict[str, Any]:
        """
        Convert discussion + cluster context into report JSON: answer, rationale, key_metrics.
        Used to feed ReportGenerator.generate_pdf(). key_metrics must include category names
        so the report can render Metrics Analysis charts (MetricParser extracts category from text).
        """
        prompt = f"""You are preparing structured data for a CRM analytics PDF report that includes metrics analysis and graphs.

Cluster context: "{parent_label}" (sub-cluster: "{child_label}").
Discussion text (what we showed the user about the analytics view): {discussion}

Output a JSON object with exactly these keys:

- "answer": One or two sentences summarizing the main finding (use the discussion as the basis).
- "rationale": Array of 2-5 short bullet-point strings with specific insights and numbers (e.g. "Recreation leads with 663 requests (18.5%)", "Roads second with 562 requests (15.68%)").
- "key_metrics": Array of metric strings that MUST include the category name so charts can be generated. Use these exact patterns:
  * For volume: "X requests in CategoryName" or "X recent requests in CategoryName" (e.g. "663 recent requests in Recreation and leisure")
  * For growth: "X% growth in CategoryName" (e.g. "73.1% growth in Recreation and leisure")
  * For increase: "X requests increase in CategoryName" (e.g. "280 requests increase in Recreation and leisure")
  * For percentage of total: "X% in CategoryName" (e.g. "18.5% in Recreation and leisure")
  Include 5-12 key_metrics covering the main categories and numbers from the discussion. Each metric string must contain both a number and a category name (e.g. "Recreation and leisure", "Roads, traffic and sidewalks", "Trees").

Example key_metrics format:
["663 recent requests in Recreation and leisure", "18.5% in Recreation and leisure", "73.1% growth in Recreation and leisure", "562 recent requests in Roads, traffic and sidewalks", "15.68% in Roads, traffic and sidewalks", "280 requests increase in Recreation and leisure"]

Return ONLY valid JSON, no markdown or code fences."""

        _log_prompt_to_console("report_data_from_discussion", prompt)
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            text = response.text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
                if text.startswith("json"):
                    text = text[4:].strip()
            data = json.loads(text)
            answer = data.get("answer", discussion[:500])
            rationale = data.get("rationale", [])
            if not isinstance(rationale, list):
                rationale = [str(rationale)]
            key_metrics = data.get("key_metrics", [])
            if not isinstance(key_metrics, list):
                key_metrics = [str(key_metrics)]
            return {"answer": answer, "rationale": rationale, "key_metrics": key_metrics}
        except Exception as e:
            print(f"Error in report_data_from_discussion: {e}")
            return {
                "answer": discussion[:500] if discussion else "Analysis complete.",
                "rationale": [s.strip() for s in discussion.split(".") if s.strip()][:4],
                "key_metrics": [],
            }

    def simple_chat(self, user_question: str) -> str:
        """
        Simple chatbot mode - direct conversation with Gemini
        No data retrieval, just conversational responses with context
        
        Args:
            user_question: The user's question
            
        Returns:
            String response from Gemini
        """
        
        prompt = f"""You are an intelligent assistant to the Mayor, specializing in municipal service requests and CRM data.

You have knowledge about:
- Municipal service request categories (roads, traffic, sidewalks, recreation, parks, etc.)
- Service request lifecycle and management
- Common municipal operations and priorities
- How cities handle citizen requests and complaints

The user is asking you a question. Reply in 1-3 short sentences only. Be as brief as possible while still helpful. No long explanations.

If the user asks about specific data or analytics, say they can use "analysis" for deep data analysis.

USER QUESTION:
{user_question}

Your response:"""

        _log_prompt_to_console("simple_chat", prompt)
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"Error in simple chat: {e}")
            raise
