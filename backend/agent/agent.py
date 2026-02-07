"""
Main CRM Analytics Agent orchestrating the two-stage Gemini process
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from backend/.env
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

from .catalog import get_catalog_summary
from .data_loader import DataLoader
from .gemini_client import GeminiAgent


class CRMAnalyticsAgent:
    """
    Orchestrates the two-stage Gemini analysis process:
    1. Planning: Determine which data products to use
    2. Analysis: Generate final answer with retrieved data
    """
    
    def __init__(self, gemini_api_key: Optional[str] = None, data_dir: Optional[str] = None):
        """
        Initialize the agent
        
        Args:
            gemini_api_key: Google AI API key (or reads from GEMINI_API_KEY env var)
            data_dir: Path to data directory (defaults to backend/trends/data)
        """
        self.gemini_agent = GeminiAgent(api_key=gemini_api_key)
        self.data_loader = DataLoader(data_dir=data_dir)
        self.catalog_summary = get_catalog_summary()
    
    def _get_frequency_preview(self, num_rows: int = 10) -> str:
        """Get a preview of frequency_over_time.csv for the planning stage"""
        df = self.data_loader.load_product("frequency_over_time")
        if df is None:
            return "Frequency data not available"
        
        return self.data_loader.get_data_summary(df, max_rows=num_rows)
    
    def query(self, user_question: str, verbose: bool = True) -> Dict[str, Any]:
        """
        Process a user question through the two-stage pipeline
        
        Args:
            user_question: The user's question about CRM data
            verbose: If True, print progress information
            
        Returns:
            Dictionary containing the complete analysis results:
            {
                "question": str,
                "plan": List[Dict],
                "fetched_products": List[str],
                "answer": str,
                "rationale": List[str],
                "key_metrics": List[str],
                "raw_data": Dict (optional, if you want to include raw data)
            }
        """
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"QUESTION: {user_question}")
            print(f"{'='*80}\n")
        
        # STAGE 1: Planning
        if verbose:
            print("🤔 Stage 1: Planning which data products to use...")
        
        frequency_preview = self._get_frequency_preview()
        plan = self.gemini_agent.plan_stage(
            user_question=user_question,
            catalog_summary=self.catalog_summary,
            frequency_data_preview=frequency_preview
        )
        
        if verbose:
            print(f"\n📋 Plan generated:")
            for item in plan:
                print(f"   - {item['product']}: {item['why']}")
            print()
        
        # STAGE 2: Fetch data products (using summaries if available)
        if verbose:
            print("📊 Stage 2: Fetching data products...")
        
        product_ids = [item["product"] for item in plan]
        
        # Try to load pre-generated summaries first (much faster!)
        fetched_data_summaries = self.data_loader.load_multiple_summaries(product_ids)
        
        if verbose:
            print(f"   Loaded {len(fetched_data_summaries)} data products")
            for product_id in fetched_data_summaries.keys():
                # Check if it was from a pre-generated summary
                summary_exists = (self.data_loader.summary_dir / f"{product_id}.txt").exists()
                marker = "📄" if summary_exists else "💾"
                print(f"   {marker} {product_id}")
            print()
        
        # STAGE 3: Analysis
        if verbose:
            print("🧠 Stage 3: Generating final analysis...")
        
        result = self.gemini_agent.analysis_stage(
            user_question=user_question,
            access_log=plan,
            fetched_data=fetched_data_summaries
        )
        
        if verbose:
            print(f"\n{'='*80}")
            print("✨ FINAL ANSWER")
            print(f"{'='*80}")
            print(f"\n{result.get('answer', 'No answer generated')}\n")
            
            if 'rationale' in result:
                print("📌 RATIONALE:")
                for point in result['rationale']:
                    print(f"   • {point}")
                print()
            
            if 'key_metrics' in result:
                print("🔢 KEY METRICS:")
                for metric in result['key_metrics']:
                    print(f"   • {metric}")
                print()
            
            print(f"{'='*80}\n")
        
        # Compile complete response
        complete_response = {
            "question": user_question,
            "plan": plan,
            "fetched_products": list(fetched_data_summaries.keys()),
            "answer": result.get("answer", ""),
            "rationale": result.get("rationale", []),
            "key_metrics": result.get("key_metrics", []),
        }
        
        return complete_response
    
    def batch_query(self, questions: list, verbose: bool = True) -> list:
        """
        Process multiple questions
        
        Args:
            questions: List of question strings
            verbose: If True, print progress for each question
            
        Returns:
            List of response dictionaries
        """
        results = []
        
        for i, question in enumerate(questions, 1):
            if verbose:
                print(f"\n\n{'#'*80}")
                print(f"QUESTION {i} of {len(questions)}")
                print(f"{'#'*80}")
            
            result = self.query(question, verbose=verbose)
            results.append(result)
        
        return results


# Example usage function
def main():
    """Example usage of the CRM Analytics Agent"""
    
    # Initialize agent (make sure GEMINI_API_KEY is set in environment)
    agent = CRMAnalyticsAgent()
    
    # Example questions
    questions = [
        "What are the top service categories by volume in the last 30 days?",
        "Which service categories have the worst response times and oldest backlog?",
        "What are the seasonal trends in garbage and recycling requests?",
    ]
    
    # Process a single question
    result = agent.query(questions[0])
    
    # Or process multiple questions
    # results = agent.batch_query(questions)
    
    return result


if __name__ == "__main__":
    main()
