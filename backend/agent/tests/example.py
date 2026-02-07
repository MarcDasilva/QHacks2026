"""
Example usage of the CRM Analytics Agent
Run this script to test the agent with sample questions
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path if running from agent folder
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

# Load environment variables from backend/.env
env_path = backend_path / ".env"
if env_path.exists():
    load_dotenv(env_path)

from agent import CRMAnalyticsAgent


def main():
    """Run example queries"""
    
    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  WARNING: GEMINI_API_KEY environment variable not set!")
        print("Please set it before running:")
        print("  PowerShell: $env:GEMINI_API_KEY=\"your-key-here\"")
        print("  Bash: export GEMINI_API_KEY=\"your-key-here\"")
        print("\nYou can get a free API key at: https://makersuite.google.com/app/apikey")
        print("\nAttempting to continue anyway...\n")
    
    # Initialize agent
    print("🚀 Initializing CRM Analytics Agent...\n")
    try:
        agent = CRMAnalyticsAgent()
    except ValueError as e:
        print(f"❌ Error: {e}")
        return
    
    # Example questions to test
    example_questions = [
        "Which categories are trending upward the most?",
        "What are the top 3 service categories by volume in the last 30 days?",
        "Which service categories have the oldest backlogs?",
        "What are the top geographic hotspots for service requests?",
    ]
    
    # Let user choose or run first example
    print("📋 Example Questions:")
    for i, q in enumerate(example_questions, 1):
        print(f"  {i}. {q}")
    print()
    
    # Run the first example
    print(f"Running example 1...\n")
    result = agent.query(example_questions[0], verbose=True)
    
    # Optionally save results
    print("\n💾 Results saved to result variable")
    print("\nTo run other examples:")
    print("  result = agent.query(example_questions[1])")
    print("  result = agent.query('Your custom question here')")
    
    return result


if __name__ == "__main__":
    result = main()
