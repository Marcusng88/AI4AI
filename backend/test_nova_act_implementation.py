#!/usr/bin/env python3
"""
Test script to verify the Nova Act implementation works correctly.
This script tests the subprocess isolation approach.
"""

import os
import sys
import json
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.agents.automation.nova_act_agent import nova_act_agent

def test_nova_act_implementation():
    """Test the Nova Act implementation with a simple execution plan."""
    
    print("🧪 Testing Nova Act Implementation...")
    print("=" * 50)
    
    # Create a simple execution plan
    execution_plan = {
        "session_id": f"test_session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "task_description": "Test Nova Act implementation",
        "target_website": "https://www.google.com",
        "micro_steps": [
            {
                "step_number": 1,
                "instruction": "Navigate to Google search page",
                "nova_act_type": "navigate",
                "timeout_seconds": 30,
                "blackhole_detection": {
                    "max_consecutive_failures": 3,
                    "max_similar_errors": 2,
                    "monitoring_keywords": ["error", "failed", "timeout"]
                }
            },
            {
                "step_number": 2,
                "instruction": "Search for 'Nova Act automation'",
                "nova_act_type": "search",
                "timeout_seconds": 30,
                "blackhole_detection": {
                    "max_consecutive_failures": 3,
                    "max_similar_errors": 2,
                    "monitoring_keywords": ["error", "failed", "timeout"]
                }
            }
        ],
        "execution_strategy": "sequential",
        "estimated_duration": 60,
        "priority": "medium"
    }
    
    print(f"📋 Execution Plan:")
    print(f"   Task: {execution_plan['task_description']}")
    print(f"   Target: {execution_plan['target_website']}")
    print(f"   Steps: {len(execution_plan['micro_steps'])}")
    print()
    
    try:
        # Execute the plan
        print("🚀 Executing Nova Act plan...")
        result = nova_act_agent.execute_execution_plan(execution_plan)
        
        print("✅ Execution completed!")
        print()
        print("📊 Results:")
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Message: {result.get('message', 'No message')}")
        print(f"   Success Count: {result.get('success_count', 0)}")
        print(f"   Failed Count: {result.get('failed_count', 0)}")
        print(f"   Requires Human: {result.get('requires_human', False)}")
        
        if 'results' in result:
            print(f"   Total Results: {len(result['results'])}")
            for i, step_result in enumerate(result['results']):
                print(f"     Step {i+1}: {step_result.get('status', 'unknown')} - {step_result.get('instruction', 'No instruction')[:50]}...")
        
        return result
        
    except Exception as e:
        print(f"❌ Error during execution: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Check if required environment variables are set
    required_env_vars = ["NOVA_ACT_API_KEY", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these environment variables before running the test.")
        sys.exit(1)
    
    print("🔧 Environment variables check passed!")
    print()
    
    # Run the test
    result = test_nova_act_implementation()
    
    if result and result.get('status') == 'success':
        print("\n🎉 Test completed successfully!")
    else:
        print("\n⚠️  Test completed with issues.")
        if result:
            print(f"   Status: {result.get('status', 'unknown')}")
            print(f"   Message: {result.get('message', 'No message')}")
