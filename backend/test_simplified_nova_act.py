#!/usr/bin/env python3
"""
Test script for the simplified Nova Act implementation with BOOL_SCHEMA error detection
and CrewAI LLM-based result processing.
"""

import os
import sys
import json
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.agents.automation.nova_act_agent import nova_act_agent
from app.agents.automation.automation_agent import automation_agent

def test_simplified_nova_act():
    """Test the simplified Nova Act implementation."""
    
    print("🧪 Testing Simplified Nova Act Implementation...")
    print("=" * 60)
    
    # Create a simple execution plan
    execution_plan = {
        "session_id": f"test_session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "task_description": "Test simplified Nova Act with BOOL_SCHEMA error detection",
        "target_website": "https://www.google.com",
        "micro_steps": [
            {
                "step_number": 1,
                "instruction": "Navigate to Google search page",
                "nova_act_type": "navigate",
                "timeout_seconds": 30
            },
            {
                "step_number": 2,
                "instruction": "Search for 'Nova Act automation'",
                "nova_act_type": "search",
                "timeout_seconds": 30
            }
        ],
        "execution_strategy": "sequential"
    }
    
    print(f"📋 Execution Plan:")
    print(f"   Task: {execution_plan['task_description']}")
    print(f"   Target: {execution_plan['target_website']}")
    print(f"   Steps: {len(execution_plan['micro_steps'])}")
    print()
    
    try:
        # Execute the plan with Nova Act
        print("🚀 Executing Nova Act plan with BOOL_SCHEMA error detection...")
        nova_act_result = nova_act_agent.execute_execution_plan(execution_plan)
        
        print("✅ Nova Act execution completed!")
        print()
        print("📊 Nova Act Results:")
        print(f"   Status: {nova_act_result.get('status', 'unknown')}")
        print(f"   Message: {nova_act_result.get('message', 'No message')}")
        print(f"   Success Count: {nova_act_result.get('success_count', 0)}")
        print(f"   Failed Count: {nova_act_result.get('failed_count', 0)}")
        print(f"   Requires Human: {nova_act_result.get('requires_human', False)}")
        
        if 'error_detection' in nova_act_result and nova_act_result['error_detection'] is not None:
            error_detection = nova_act_result['error_detection']
            print(f"   Error Detection:")
            print(f"     Has Difficulties: {error_detection.get('has_difficulties', False)}")
            print(f"     Is Stuck in Loop: {error_detection.get('is_stuck_in_loop', False)}")
            print(f"     Can Proceed: {error_detection.get('can_proceed', False)}")
            print(f"     Error Type: {error_detection.get('error_type', 'None')}")
        else:
            print(f"   Error Detection: None")
        
        print()
        
        # Test CrewAI LLM-based result processing
        print("🤖 Testing CrewAI LLM-based result processing...")
        original_task = {
            "task_description": execution_plan['task_description'],
            "target_website": execution_plan['target_website']
        }
        
        processed_result = automation_agent.process_nova_act_result(nova_act_result, original_task)
        
        print("✅ CrewAI result processing completed!")
        print()
        print("📊 Processed Results:")
        print(f"   Status: {processed_result.get('status', 'unknown')}")
        print(f"   Message: {processed_result.get('message', 'No message')}")
        print(f"   Action: {processed_result.get('action', 'unknown')}")
        print(f"   Requires Human: {processed_result.get('requires_human', False)}")
        
        if 'confidence' in processed_result:
            print(f"   Confidence: {processed_result.get('confidence', 0.0):.2f}")
        
        if 'reasoning' in processed_result:
            print(f"   Reasoning: {processed_result.get('reasoning', 'No reasoning')}")
        
        if 'improvement_suggestions' in processed_result:
            suggestions = processed_result.get('improvement_suggestions', [])
            if suggestions:
                print(f"   Improvement Suggestions:")
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"     {i}. {suggestion}")
        
        if 'tutorial' in processed_result:
            tutorial = processed_result.get('tutorial', '')
            if tutorial:
                print(f"   Tutorial: {tutorial[:200]}...")
        
        return {
            "nova_act_result": nova_act_result,
            "processed_result": processed_result
        }
        
    except Exception as e:
        print(f"❌ Error during execution: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_error_detection_scenarios():
    """Test different error detection scenarios."""
    
    print("\n🔍 Testing Error Detection Scenarios...")
    print("=" * 60)
    
    # Test scenarios
    scenarios = [
        {
            "name": "Success Scenario",
            "nova_act_result": {
                "status": "success",
                "message": "All steps completed successfully",
                "success_count": 2,
                "failed_count": 0,
                "requires_human": False,
                "error_detection": {
                    "has_difficulties": False,
                    "is_stuck_in_loop": False,
                    "can_proceed": True,
                    "error_type": None
                }
            }
        },
        {
            "name": "Partial Failure Scenario",
            "nova_act_result": {
                "status": "partial",
                "message": "Some steps completed, others failed",
                "success_count": 1,
                "failed_count": 1,
                "requires_human": True,
                "error_detection": {
                    "has_difficulties": True,
                    "is_stuck_in_loop": False,
                    "can_proceed": False,
                    "error_type": "general_difficulties"
                },
                "suggestions": ["Try refreshing the page", "Check for popup blockers"]
            }
        },
        {
            "name": "Infinite Loop Scenario",
            "nova_act_result": {
                "status": "failed",
                "message": "Execution stopped due to infinite loop",
                "success_count": 0,
                "failed_count": 2,
                "requires_human": True,
                "error_detection": {
                    "has_difficulties": True,
                    "is_stuck_in_loop": True,
                    "can_proceed": False,
                    "error_type": "infinite_loop"
                },
                "suggestions": ["Stop execution to prevent infinite loops"]
            }
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📝 Testing: {scenario['name']}")
        print("-" * 40)
        
        try:
            original_task = {
                "task_description": "Test automation task",
                "target_website": "https://example.com"
            }
            
            processed_result = automation_agent.process_nova_act_result(
                scenario['nova_act_result'], 
                original_task
            )
            
            print(f"   Decision: {processed_result.get('action', 'unknown')}")
            print(f"   Message: {processed_result.get('message', 'No message')}")
            print(f"   Requires Human: {processed_result.get('requires_human', False)}")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

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
    
    # Run the main test
    result = test_simplified_nova_act()
    
    if result:
        print("\n🎉 Main test completed!")
        
        # Run error detection scenario tests
        test_error_detection_scenarios()
        
        print("\n🎉 All tests completed!")
    else:
        print("\n⚠️  Main test failed.")
