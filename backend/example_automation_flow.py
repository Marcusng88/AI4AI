"""
Example of the two-stage automation flow:
1. Automation Agent generates structured execution plan
2. Nova Act Agent executes the plan

Key Points:
- Automation Agent generates complete structured plan with all micro-steps
- Nova Act Agent receives entire plan and executes ALL steps using browser_session context manager
- Uses correct Nova Act pattern with agentcore browser
- No back-and-forth between agents during execution
"""

import asyncio
from app.agents.automation.automation_agent import AutomationAgent
from app.agents.automation.nova_act_agent import NovaActAgent


async def example_automation_flow():
    """Example of the complete automation flow."""
    
    # Sample task with validation result
    task = {
        "task_description": "Apply for JPJ driving license renewal",
        "validation_result": {
            "validation_status": "passed",
            "confidence_score": 0.85,
            "micro_steps": [
                {
                    "step_number": 1,
                    "action_type": "navigate",
                    "instruction": "Navigate to JPJ website",
                    "target_element": "website",
                    "validation_criteria": "Verify page loaded successfully"
                },
                {
                    "step_number": 2,
                    "action_type": "click",
                    "instruction": "Click on driving license renewal link",
                    "target_element": "renewal link",
                    "validation_criteria": "Verify renewal page opened"
                },
                {
                    "step_number": 3,
                    "action_type": "input",
                    "instruction": "Fill in personal details form",
                    "target_element": "form fields",
                    "validation_criteria": "Verify form filled successfully"
                },
                {
                    "step_number": 4,
                    "action_type": "click",
                    "instruction": "Submit the application",
                    "target_element": "submit button",
                    "validation_criteria": "Verify application submitted"
                }
            ],
            "corrected_flow": {
                "original_flow": {
                    "target_websites": ["https://www.jpj.gov.my"]
                }
            }
        }
    }
    
    print("=== AUTOMATION AGENT STAGE ===")
    print("Generating structured execution plan...")
    
    # Stage 1: Automation Agent generates execution plan
    automation_agent = AutomationAgent()
    execution_plan_result = automation_agent.generate_execution_plan(task)
    
    if execution_plan_result["status"] != "success":
        print(f"❌ Automation Agent failed: {execution_plan_result['message']}")
        return
    
    execution_plan = execution_plan_result["execution_plan"]
    print(f"✅ Execution plan generated successfully!")
    print(f"   Session ID: {execution_plan['session_id']}")
    print(f"   Target Website: {execution_plan['target_website']}")
    print(f"   Micro-steps: {len(execution_plan['micro_steps'])}")
    print(f"   Execution Strategy: {execution_plan['execution_strategy']}")
    print(f"   Confidence Score: {execution_plan['confidence_score']}")
    print(f"   Estimated Time: {execution_plan['total_estimated_time']} seconds")
    
    print("\n=== NOVA ACT AGENT STAGE ===")
    print("Executing the structured plan...")
    
    # Stage 2: Nova Act Agent executes the plan
    nova_act_agent = NovaActAgent()
    execution_result = await nova_act_agent.execute_execution_plan(execution_plan)
    
    if execution_result["status"] == "success":
        print(f"✅ Automation completed successfully!")
        print(f"   Session ID: {execution_result['session_id']}")
        print(f"   Success Count: {execution_result['success_count']}")
        print(f"   Failed Count: {execution_result['failed_count']}")
    elif execution_result["status"] == "partial":
        print(f"⚠️  Automation completed with some failures")
        print(f"   Success Count: {execution_result['success_count']}")
        print(f"   Failed Count: {execution_result['failed_count']}")
    else:
        print(f"❌ Automation failed: {execution_result['message']}")
    
    print("\n=== EXECUTION DETAILS ===")
    for i, result in enumerate(execution_result.get('results', []), 1):
        status_emoji = "✅" if result['status'] == "success" else "❌"
        print(f"   Step {i}: {status_emoji} {result['instruction'][:50]}...")
        if result['status'] == "failed":
            print(f"      Error: {result['error_message']}")


if __name__ == "__main__":
    asyncio.run(example_automation_flow())
