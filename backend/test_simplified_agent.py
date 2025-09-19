#!/usr/bin/env python3
"""
Test script for the simplified agent approach with memory and prompting.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.agents.coordinator.coordinator_agent import coordinator_agent

async def test_simplified_agent():
    """Test the simplified agent with memory and prompting."""
    
    print("🤖 Testing Simplified Agent with Memory and Prompting")
    print("=" * 60)
    
    # Test 1: Basic government service request
    print("\n📋 Test 1: Basic JPJ Service Request")
    print("-" * 40)
    
    result1 = await coordinator_agent.process_user_request(
        user_message="I want to renew my driving license",
        user_context={},
        session_id="test_session_1",
        user_id="test_user_1"
    )
    
    print(f"Status: {result1.get('status')}")
    print(f"Message: {result1.get('message')}")
    print(f"Requires Human: {result1.get('requires_human')}")
    
    if result1.get('missing_information'):
        print(f"Missing Information: {result1.get('missing_information')}")
    
    # Test 2: Follow-up with information
    print("\n📋 Test 2: Follow-up with IC Number")
    print("-" * 40)
    
    result2 = await coordinator_agent.process_user_request(
        user_message="My IC number is 901234567890",
        user_context={"ic_number": "901234567890"},
        session_id="test_session_1",
        user_id="test_user_1"
    )
    
    print(f"Status: {result2.get('status')}")
    print(f"Message: {result2.get('message')}")
    print(f"Requires Human: {result2.get('requires_human')}")
    
    # Test 3: Memory test - ask about previous request
    print("\n📋 Test 3: Memory Test - Previous Request")
    print("-" * 40)
    
    result3 = await coordinator_agent.process_user_request(
        user_message="What was I asking about before?",
        user_context={},
        session_id="test_session_1",
        user_id="test_user_1"
    )
    
    print(f"Status: {result3.get('status')}")
    print(f"Message: {result3.get('message')}")
    print(f"Requires Human: {result3.get('requires_human')}")
    
    # Test 4: Non-government service
    print("\n📋 Test 4: Non-Government Service")
    print("-" * 40)
    
    result4 = await coordinator_agent.process_user_request(
        user_message="I want to order pizza",
        user_context={},
        session_id="test_session_2",
        user_id="test_user_2"
    )
    
    print(f"Status: {result4.get('status')}")
    print(f"Message: {result4.get('message')}")
    print(f"Requires Human: {result4.get('requires_human')}")
    
    print("\n✅ Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_simplified_agent())
