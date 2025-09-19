#!/usr/bin/env python3
"""
Test Script for CrewAI Government Services Automation Agent
==========================================================

This script tests the CrewAI agent with Stagehand integration for government services automation.
It includes tests for various government service tasks including traffic summons checking,
document downloads, and form submissions.

Usage:
    python test_crewai_government_agent.py
"""

import asyncio
import sys
import os
import json
from typing import Dict, Any
import logging
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.agents.stagehand.stagehand_agent import (
    GovernmentServicesAgent,
    StagehandTool,
    check_traffic_summons,
    download_government_document,
    submit_government_form
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_government_agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class GovernmentAgentTester:
    """Test harness for the CrewAI Government Services Agent"""
    
    def __init__(self):
        self.agent = None
        self.test_results = []
        
    async def setup(self):
        """Initialize the agent for testing"""
        try:
            logger.info("Setting up GovernmentServicesAgent...")
            self.agent = GovernmentServicesAgent()
            logger.info("Agent setup completed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to setup agent: {str(e)}")
            return False
    
    def log_test_result(self, test_name: str, success: bool, message: str, details: Dict = None):
        """Log test results"""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{status} - {test_name}: {message}")
        
        if details:
            logger.info(f"Details: {json.dumps(details, indent=2)}")
    
    async def test_stagehand_tool_basic(self):
        """Test basic StagehandTool functionality"""
        test_name = "StagehandTool Basic Functionality"
        
        try:
            tool = StagehandTool()
            
            # Test tool properties
            assert tool.name == "browser_automation"
            assert tool.description is not None
            assert len(tool.description) > 0
            
            self.log_test_result(
                test_name, 
                True, 
                "StagehandTool initialized successfully with correct properties",
                {"name": tool.name, "description_length": len(tool.description)}
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                test_name, 
                False, 
                f"StagehandTool initialization failed: {str(e)}"
            )
            return False
    
    async def test_agent_setup(self):
        """Test agent setup and configuration"""
        test_name = "Agent Setup and Configuration"
        
        try:
            # Check if agents are properly initialized
            assert self.agent is not None
            assert hasattr(self.agent, 'navigator_agent')
            assert hasattr(self.agent, 'extractor_agent')
            assert hasattr(self.agent, 'form_agent')
            assert hasattr(self.agent, 'stagehand_tool')
            
            # Check agent properties
            navigator = self.agent.navigator_agent
            extractor = self.agent.extractor_agent
            form_agent = self.agent.form_agent
            
            assert navigator.role == "Government Portal Navigator"
            assert extractor.role == "Government Data Extractor"
            assert form_agent.role == "Government Form Automation Specialist"
            
            self.log_test_result(
                test_name,
                True,
                "All agents initialized with correct roles and configurations",
                {
                    "navigator_role": navigator.role,
                    "extractor_role": extractor.role,
                    "form_agent_role": form_agent.role,
                    "tools_count": len(navigator.tools)
                }
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                test_name,
                False,
                f"Agent setup validation failed: {str(e)}"
            )
            return False
    
    async def test_task_creation(self):
        """Test task creation for different government services"""
        test_name = "Task Creation"
        
        try:
            # Test traffic summons task creation
            traffic_task = self.agent.create_traffic_summons_task(
                ic_number="123456789012",
                username="test_user",
                password="test_pass"
            )
            
            assert traffic_task is not None
            assert traffic_task.description is not None
            assert "123456789012" in traffic_task.description
            assert traffic_task.agent == self.agent.navigator_agent
            
            # Test document download task creation
            doc_task = self.agent.create_document_download_task(
                portal_url="https://example.gov.my",
                document_type="Certificate",
                search_criteria={"id": "123456", "year": "2024"}
            )
            
            assert doc_task is not None
            assert doc_task.description is not None
            assert "Certificate" in doc_task.description
            assert doc_task.agent == self.agent.extractor_agent
            
            # Test form submission task creation
            form_task = self.agent.create_form_submission_task(
                portal_url="https://example.gov.my/form",
                form_data={"name": "Test User", "ic": "123456789012"},
                form_type="Application"
            )
            
            assert form_task is not None
            assert form_task.description is not None
            assert "Application" in form_task.description
            assert form_task.agent == self.agent.form_agent
            
            self.log_test_result(
                test_name,
                True,
                "All task types created successfully",
                {
                    "traffic_task_created": True,
                    "document_task_created": True,
                    "form_task_created": True
                }
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                test_name,
                False,
                f"Task creation failed: {str(e)}"
            )
            return False
    
    async def test_convenience_functions(self):
        """Test convenience functions for common operations"""
        test_name = "Convenience Functions"
        
        try:
            # Test that convenience functions exist and are callable
            assert callable(check_traffic_summons)
            assert callable(download_government_document)
            assert callable(submit_government_form)
            
            self.log_test_result(
                test_name,
                True,
                "All convenience functions are available and callable"
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                test_name,
                False,
                f"Convenience functions test failed: {str(e)}"
            )
            return False
    
    async def test_myeg_traffic_summons_simulation(self):
        """Simulate MyEG traffic summons checking (without actual execution)"""
        test_name = "MyEG Traffic Summons Simulation"
        
        try:
            # Create a traffic summons task
            task = self.agent.create_traffic_summons_task(
                ic_number="123456789012",
                username="ngzhengjie888@gmail.com",
                password="Nzj@755788"
            )
            
            # Verify task contains MyEG specific information
            description = task.description.lower()
            assert "myeg.com.my" in description
            assert "jabatan pengangkutan jalan" in description
            assert "check & pay rtd summons" in description
            assert "123456789012" in description
            
            self.log_test_result(
                test_name,
                True,
                "MyEG traffic summons task created with correct parameters",
                {
                    "contains_myeg_url": "myeg.com.my" in description,
                    "contains_jpj_navigation": "jabatan pengangkutan jalan" in description,
                    "contains_ic_number": "123456789012" in description
                }
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                test_name,
                False,
                f"MyEG simulation failed: {str(e)}"
            )
            return False
    
    async def test_error_handling(self):
        """Test error handling for invalid inputs"""
        test_name = "Error Handling"
        
        try:
            # Test invalid task type
            result = await self.agent.execute_government_task("invalid_task_type")
            assert "Error: Unknown task type" in result
            
            # Test missing required parameters
            result = await self.agent.execute_government_task("traffic_summons")
            # Should handle missing ic_number gracefully
            
            self.log_test_result(
                test_name,
                True,
                "Error handling working correctly for invalid inputs"
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                test_name,
                False,
                f"Error handling test failed: {str(e)}"
            )
            return False
    
    async def run_all_tests(self):
        """Run all tests and generate report"""
        logger.info("🚀 Starting CrewAI Government Services Agent Tests")
        logger.info("=" * 60)
        
        # Setup phase
        setup_success = await self.setup()
        if not setup_success:
            logger.error("❌ Setup failed. Aborting tests.")
            return False
        
        # Run all tests
        tests = [
            self.test_stagehand_tool_basic,
            self.test_agent_setup,
            self.test_task_creation,
            self.test_convenience_functions,
            self.test_myeg_traffic_summons_simulation,
            self.test_error_handling
        ]
        
        total_tests = len(tests)
        passed_tests = 0
        
        for test in tests:
            try:
                result = await test()
                if result:
                    passed_tests += 1
            except Exception as e:
                logger.error(f"Test {test.__name__} crashed: {str(e)}")
        
        # Generate report
        logger.info("=" * 60)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {total_tests - passed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            logger.info("🎉 All tests passed! The CrewAI Government Services Agent is ready for use.")
        else:
            logger.warning("⚠️  Some tests failed. Please review the issues above.")
        
        # Save detailed results
        with open('test_results.json', 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        logger.info("📄 Detailed test results saved to test_results.json")
        return passed_tests == total_tests


async def main():
    """Main test function"""
    print("🤖 CrewAI Government Services Agent - Test Suite")
    print("=" * 50)
    
    tester = GovernmentAgentTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ All tests passed! You can now use the agent.")
        print("\n📝 Example usage:")
        print("```python")
        print("from app.agents.stagehand.stagehand_agent import check_traffic_summons")
        print("")
        print("# Check traffic summons")
        print("result = await check_traffic_summons(")
        print("    ic_number='123456789012',")
        print("    username='your_email@gmail.com',")
        print("    password='your_password'")
        print(")")
        print("print(result)")
        print("```")
    else:
        print("\n❌ Some tests failed. Please check the logs for details.")
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {str(e)}")
        sys.exit(1)
