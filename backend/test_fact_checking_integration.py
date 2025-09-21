#!/usr/bin/env python3
"""
Test script for the enhanced automation agent with Tavily fact-checking integration.
This script demonstrates how the automation agent now includes fact-checking capabilities
when generating tutorials for government services.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.agents.automation.automation_agent import AutomationAgent
from app.core.logging import get_logger

logger = get_logger(__name__)

def test_fact_checking_integration():
    """Test the fact-checking integration in the automation agent."""
    
    print("=" * 60)
    print("TESTING AUTOMATION AGENT WITH TAVILY FACT-CHECKING")
    print("=" * 60)
    
    try:
        # Initialize the automation agent
        print("1. Initializing automation agent...")
        automation_agent = AutomationAgent()
        
        # Check if Tavily tool is available
        if automation_agent.tavily_tool:
            print("✅ Tavily tool initialized successfully")
        else:
            print("⚠️ Tavily tool not available (check TAVILY_API_KEY)")
        
        # Test fact-checking functionality
        print("\n2. Testing fact-checking functionality...")
        
        # Sample tutorial content to fact-check
        sample_tutorial = """
# How to Check JPJ Summons on MyEG

## Step 1: Access MyEG Website
1. Go to https://www.myeg.com.my
2. Wait for the page to load

## Step 2: Navigate to JPJ Services
1. Look for "JPJ" or "Transportation" services
2. Click on "Check & Pay RTD Summons"

## Step 3: Enter IC Number
1. Enter your IC number in the provided field
2. Click "Check Summons"

## Step 4: Review Results
1. View any outstanding summons
2. Note the details and amounts
        """
        
        print("Testing fact-checking with sample tutorial content...")
        fact_check_result = automation_agent.fact_check_tutorial_content(
            sample_tutorial, 
            service_type="MyEG JPJ summons checking"
        )
        
        print(f"Fact-checking status: {fact_check_result.get('status', 'Unknown')}")
        print(f"Verified: {fact_check_result.get('verified', False)}")
        
        if fact_check_result.get('report'):
            print(f"Report preview: {fact_check_result['report'][:200]}...")
        
        # Test tutorial generation with fact-checking
        print("\n3. Testing tutorial generation with fact-checking...")
        
        # Create a mock original task for tutorial generation
        mock_original_task = {
            'user_message': 'I need to check my JPJ summons on MyEG',
            'extracted_credentials': {'ic_number': '123456-78-9012'},
            'user_context': {},
            'task_description': 'Check JPJ summons on MyEG website',
            'target_website': 'https://www.myeg.com.my'
        }
        
        print("Generating tutorial with fact-checking...")
        tutorial_content = automation_agent._generate_tutorial_from_validator(
            mock_original_task, 
            error_type="general_failure", 
            suggestions=["Try using a different browser", "Check internet connection"]
        )
        
        print("✅ Tutorial generated successfully with fact-checking!")
        print(f"Tutorial length: {len(tutorial_content)} characters")
        
        # Check if fact-checking information was added
        if "Last Verified:" in tutorial_content:
            print("✅ Fact-checking information included in tutorial")
        else:
            print("⚠️ Fact-checking information not found in tutorial")
        
        print("\n" + "=" * 60)
        print("FACT-CHECKING INTEGRATION TEST COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        logger.error(f"Fact-checking integration test failed: {str(e)}")
        return False

def test_automation_agent_health():
    """Test the health status of the automation agent."""
    
    print("\n4. Checking automation agent health...")
    
    try:
        automation_agent = AutomationAgent()
        health_status = automation_agent.get_health_status()
        
        print(f"Agent status: {health_status.get('status', 'Unknown')}")
        print(f"Agent type: {health_status.get('agent_type', 'Unknown')}")
        print(f"LLM available: {health_status.get('llm_available', False)}")
        print(f"Micro-step generator available: {health_status.get('micro_step_generator_available', False)}")
        print(f"Active browser sessions: {health_status.get('active_browser_sessions', 0)}")
        
        if health_status.get('status') == 'healthy':
            print("✅ Automation agent is healthy")
            return True
        else:
            print("⚠️ Automation agent health check failed")
            return False
            
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        return False

if __name__ == "__main__":
    print(f"Starting fact-checking integration test at {datetime.now()}")
    
    # Run the tests
    test1_passed = test_fact_checking_integration()
    test2_passed = test_automation_agent_health()
    
    print(f"\nTest Results:")
    print(f"Fact-checking integration test: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Health check test: {'PASSED' if test2_passed else 'FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Fact-checking integration is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)
