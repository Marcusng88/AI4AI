#!/usr/bin/env python3
"""
CrewAI Government Services Agent - Demonstration Script
======================================================

This script demonstrates how to use the CrewAI Government Services Agent
for automating various government service tasks.

Usage:
    python demo_government_agent.py
"""

import asyncio
import sys
import os
import logging
from typing import Dict, Any

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.agents.stagehand.stagehand_agent import (
    GovernmentServicesAgent,
    check_traffic_summons,
    download_government_document,
    submit_government_form
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_myeg_traffic_summons():
    """
    Demonstrate MyEG traffic summons checking
    
    This example shows how to check traffic summons on the MyEG portal
    using the credentials and IC number specified in your original requirements.
    """
    print("\n🚗 Demo: MyEG Traffic Summons Checking")
    print("=" * 50)
    
    # These are the credentials from your original requirements
    username = "ngzhengjie888@gmail.com"
    password = "Nzj@755788"
    ic_number = input("Enter IC number to check (or press Enter for demo): ").strip()
    
    if not ic_number:
        ic_number = "123456789012"  # Demo IC number
        print(f"Using demo IC number: {ic_number}")
    
    try:
        print(f"Checking traffic summons for IC: {ic_number}")
        print("This will:")
        print("1. Navigate to www.myeg.com.my")
        print(f"2. Login with {username}")
        print("3. Go to Jabatan Pengangkutan Jalan > Check & Pay RTD Summons")
        print(f"4. Enter IC number: {ic_number}")
        print("5. Extract and return summons details")
        
        # Note: This would actually execute the browser automation
        result = await check_traffic_summons(
            ic_number=ic_number,
            username=username,
            password=password
        )
        
        print(f"\n✅ Result: {result}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def demo_document_download():
    """
    Demonstrate government document download
    """
    print("\n📄 Demo: Government Document Download")
    print("=" * 50)
    
    portal_url = "https://www.jpj.gov.my"
    document_type = "License Renewal Form"
    search_criteria = {
        "ic_number": "123456789012",
        "license_type": "D",
        "year": "2024"
    }
    
    try:
        print(f"Downloading {document_type} from {portal_url}")
        print(f"Search criteria: {search_criteria}")
        
        result = await download_government_document(
            portal_url=portal_url,
            document_type=document_type,
            search_criteria=search_criteria
        )
        
        print(f"\n✅ Result: {result}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def demo_form_submission():
    """
    Demonstrate government form submission
    """
    print("\n📝 Demo: Government Form Submission")
    print("=" * 50)
    
    portal_url = "https://www.hasil.gov.my"
    form_type = "Tax Filing"
    form_data = {
        "ic_number": "123456789012",
        "full_name": "Demo User",
        "email": "demo@example.com",
        "phone": "0123456789",
        "income": "50000",
        "tax_year": "2024"
    }
    
    try:
        print(f"Submitting {form_type} form to {portal_url}")
        print(f"Form data: {form_data}")
        
        result = await submit_government_form(
            portal_url=portal_url,
            form_type=form_type,
            form_data=form_data
        )
        
        print(f"\n✅ Result: {result}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def demo_custom_agent_usage():
    """
    Demonstrate direct agent usage for more complex scenarios
    """
    print("\n🤖 Demo: Custom Agent Usage")
    print("=" * 50)
    
    try:
        # Create agent instance
        agent = GovernmentServicesAgent()
        
        print("Available agents:")
        print(f"- Navigator Agent: {agent.navigator_agent.role}")
        print(f"- Extractor Agent: {agent.extractor_agent.role}")
        print(f"- Form Agent: {agent.form_agent.role}")
        
        # Example: Custom traffic summons task
        print("\nExecuting custom traffic summons task...")
        result = await agent.execute_government_task(
            "traffic_summons",
            ic_number="123456789012",
            username="ngzhengjie888@gmail.com",
            password="Nzj@755788"
        )
        
        print(f"✅ Custom task result: {result}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def main():
    """Main demonstration function"""
    print("🇲🇾 CrewAI Government Services Agent - Demonstration")
    print("=" * 60)
    print("This demo shows how to use the CrewAI agent for automating")
    print("Malaysian government service interactions.")
    print()
    
    demos = {
        "1": ("MyEG Traffic Summons", demo_myeg_traffic_summons),
        "2": ("Document Download", demo_document_download),
        "3": ("Form Submission", demo_form_submission),
        "4": ("Custom Agent Usage", demo_custom_agent_usage),
        "5": ("Run All Demos", None)
    }
    
    print("Available demonstrations:")
    for key, (name, _) in demos.items():
        print(f"  {key}. {name}")
    print("  0. Exit")
    
    while True:
        choice = input("\nSelect a demo (0-5): ").strip()
        
        if choice == "0":
            print("Goodbye!")
            break
        elif choice == "5":
            # Run all demos
            for key, (name, func) in demos.items():
                if func:  # Skip the "Run All Demos" option
                    print(f"\n🎬 Running: {name}")
                    await func()
                    input("\nPress Enter to continue to the next demo...")
        elif choice in demos and demos[choice][1]:
            name, func = demos[choice]
            print(f"\n🎬 Running: {name}")
            await func()
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n💥 Demo crashed: {str(e)}")
        sys.exit(1)
