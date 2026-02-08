"""
Gemini AI client for the two-stage prompting system
"""

import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
from google import genai

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
Return only the JSON array, nothing else."""

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

Based on the data provided above, answer the user's question with:
1. A clear, direct answer
2. A rationale with specific numbers and references from the data
3. Key insights or recommendations

Format your response as a JSON object with these keys:
- "answer": A concise answer to the question (2-3 sentences)
- "rationale": Detailed explanation with specific numbers from the data (3-5 bullet points)
- "key_metrics": List of important numbers referenced (e.g., ["663 requests in Recreation", "18.5% of total"])

IMPORTANT: Return ONLY valid JSON with no additional text, markdown, or code blocks.

Example format:
{{
  "answer": "Recreation and leisure has the highest volume with 663 requests in the last 30 days.",
  "rationale": [
    "Recreation and leisure leads with 663 requests (18.5% of total volume)",
    "Roads, traffic and sidewalks is second with 562 requests (15.68%)",
    "These top 2 categories account for over 34% of all recent requests"
  ],
  "key_metrics": ["663 requests", "18.5%", "562 requests", "15.68%"]
}}

Now analyze the data and provide your response:"""

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

The user is asking you a question. Provide a helpful, conversational response based on general knowledge about municipal services and CRM systems. Be concise and friendly.

If the user asks about specific data or analytics, you can mention that they should use the "analysis" keyword to trigger a deep data analysis with real-time data.

USER QUESTION:
{user_question}

Your response:"""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"Error in simple chat: {e}")
            raise
