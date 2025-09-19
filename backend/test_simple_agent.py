#!/usr/bin/env python3
"""
Simple test for the simplified agent approach without CrewAI dependencies.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def test_simple_flow():
    """Test the simplified flow without complex dependencies."""
    
    print("🤖 Testing Simplified Agent Flow")
    print("=" * 50)
    
    # Test the DynamoDB memory manager directly
    try:
        from app.agents.coordinator.coordinator_agent import DynamoDBMemoryManager
        
        memory_manager = DynamoDBMemoryManager()
        
        # Test saving conversation memory
        print("\n📋 Test 1: Saving Conversation Memory")
        print("-" * 40)
        
        result = await memory_manager.save_conversation_memory(
            session_id="test_session_1",
            user_id="test_user_1",
            user_message="I want to renew my driving license",
            agent_response="I can help you renew your driving license. What's your IC number?",
            context={"service": "JPJ", "type": "license_renewal"}
        )
        
        print(f"Memory saved: {result}")
        
        # Test retrieving conversation history
        print("\n📋 Test 2: Retrieving Conversation History")
        print("-" * 40)
        
        history = await memory_manager.get_conversation_history("test_session_1")
        print(f"Retrieved {len(history)} conversation(s)")
        for i, conv in enumerate(history):
            print(f"  {i+1}. User: {conv.get('user_message', '')}")
            print(f"     Agent: {conv.get('agent_response', '')}")
        
        print("\n✅ Memory system test completed!")
        
    except Exception as e:
        print(f"❌ Error testing memory system: {e}")
        print("This is expected if AWS credentials are not configured.")
    
    print("\n📋 Test 3: Simple Chat Flow Simulation")
    print("-" * 40)
    
    # Simulate the simple chat flow
    print("User: I want to renew my driving license")
    print("Agent: I can help you renew your driving license. To proceed, I need some information:")
    print("       - Your IC number")
    print("       - Your current driving license number")
    print("       - Your phone number")
    print("       Please provide these details so I can help you with the renewal process.")
    print()
    print("User: My IC is 901234567890, license is D1234567, phone is 0123456789")
    print("Agent: Thank you! I have all the information needed. I'll now help you renew your driving license...")
    print("       [Proceeds with automation]")
    
    print("\n✅ Simple flow simulation completed!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_simple_flow())
