"""
Validator Agent for Phase 1 implementation.
Validates task flows, URLs, and prepares micro-steps for automation.
"""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
import os
from crewai import Agent, Task, Crew, Process, LLM
from app.core.logging import get_logger
from app.config import settings

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Data class for validation results."""
    validation_status: str  # "passed", "failed", "needs_correction"
    corrected_flow: Dict[str, Any]
    confidence_score: float
    validation_details: str
    micro_steps: List[Dict[str, Any]]
    error_handling_plan: List[Dict[str, Any]]
    monitoring_points: List[Dict[str, Any]]


class URLValidator:
    """Utility class for URL validation."""
    
    @staticmethod
    def validate_government_url(url: str) -> Dict[str, Any]:
        """Validate if URL is a legitimate government website."""
        government_domains = [
            'gov.my', 'myeg.com.my', 'jpj.gov.my', 'hasil.gov.my', 
            'jpn.gov.my', 'kwsp.gov.my', 'ssm.com.my'
        ]
        
        validation_result = {
            'is_valid': False,
            'is_government': False,
            'is_secure': False,
            'domain': '',
            'errors': []
        }
        
        try:
            # Basic URL parsing
            if not url.startswith(('http://', 'https://')):
                validation_result['errors'].append('URL must start with http:// or https://')
                return validation_result
            
            # Extract domain
            import urllib.parse
            parsed_url = urllib.parse.urlparse(url)
            domain = parsed_url.netloc.lower()
            validation_result['domain'] = domain
            
            # Check if it's a government domain
            for gov_domain in government_domains:
                if domain.endswith(gov_domain):
                    validation_result['is_government'] = True
                    break
            
            # Check if it's secure
            if parsed_url.scheme == 'https':
                validation_result['is_secure'] = True
            
            # Overall validation
            validation_result['is_valid'] = (
                validation_result['is_government'] and 
                validation_result['is_secure'] and
                len(validation_result['errors']) == 0
            )
            
            if not validation_result['is_valid']:
                if not validation_result['is_government']:
                    validation_result['errors'].append('Not a recognized government domain')
                if not validation_result['is_secure']:
                    validation_result['errors'].append('URL is not secure (HTTPS)')
            
        except Exception as e:
            validation_result['errors'].append(f'URL parsing error: {str(e)}')
        
        return validation_result


class MicroStepGenerator:
    """Utility class for generating micro-steps for Nova Act."""
    
    @staticmethod
    def generate_micro_steps(process_steps: List[str], target_website: str) -> List[Dict[str, Any]]:
        """Generate micro-steps from process steps."""
        micro_steps = []
        
        for i, step in enumerate(process_steps, 1):
            # Analyze step to determine action type
            action_type = MicroStepGenerator._determine_action_type(step)
            
            micro_step = {
                'step_number': i,
                'action_type': action_type,
                'instruction': step,
                'target_element': MicroStepGenerator._extract_target_element(step),
                'validation_criteria': MicroStepGenerator._generate_validation_criteria(step),
                'timeout_seconds': 30,
                'retry_count': 3,
                'error_handling': MicroStepGenerator._generate_error_handling(step)
            }
            
            micro_steps.append(micro_step)
        
        return micro_steps
    
    @staticmethod
    def _determine_action_type(step: str) -> str:
        """Determine the action type from step description."""
        step_lower = step.lower()
        
        if any(word in step_lower for word in ['navigate', 'go to', 'visit', 'open']):
            return 'navigate'
        elif any(word in step_lower for word in ['login', 'sign in', 'enter credentials']):
            return 'login'
        elif any(word in step_lower for word in ['click', 'select', 'press']):
            return 'click'
        elif any(word in step_lower for word in ['fill', 'enter', 'type', 'input']):
            return 'input'
        elif any(word in step_lower for word in ['search', 'find', 'look for']):
            return 'search'
        elif any(word in step_lower for word in ['wait', 'pause']):
            return 'wait'
        else:
            return 'general'
    
    @staticmethod
    def _extract_target_element(step: str) -> str:
        """Extract target element from step description."""
        # Simple extraction - could be enhanced with NLP
        if 'button' in step.lower():
            return 'button'
        elif 'form' in step.lower():
            return 'form'
        elif 'link' in step.lower():
            return 'link'
        elif 'input' in step.lower():
            return 'input'
        else:
            return 'element'
    
    @staticmethod
    def _generate_validation_criteria(step: str) -> str:
        """Generate validation criteria for the step."""
        return f"Verify that {step.lower()} was completed successfully"
    
    @staticmethod
    def _generate_error_handling(step: str) -> Dict[str, Any]:
        """Generate error handling plan for the step."""
        return {
            'on_failure': 'retry_with_delay',
            'max_retries': 3,
            'retry_delay_seconds': 5,
            'fallback_action': 'escalate_to_human',
            'error_message': f'Failed to complete: {step}'
        }


class ValidatorAgent:
    """Validator agent for task flow validation and micro-step generation."""
    
    def __init__(self):
        # Initialize LLM
        self.llm = self._initialize_llm()
        
        # Initialize URL validator
        self.url_validator = URLValidator()
        
        # Initialize micro-step generator
        self.step_generator = MicroStepGenerator()
        
        # Initialize validator agent
        self.agent = self._create_validator_agent()
        
        logger.info("Validator agent initialized successfully")
    
    def _initialize_llm(self) -> LLM:
        """Initialize LLM for validation tasks."""
        try:
            return LLM(
                model="bedrock/amazon.nova-lite-v1:0",
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                aws_region_name=os.getenv('BEDROCK_REGION', 'ap-southeast-2'),  # Use Bedrock region
                stream=True
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {str(e)}")
            raise
    
    def _create_validator_agent(self) -> Agent:
        """Create the validator agent."""
        return Agent(
            role="Government Service Task Validator",
            goal="Validate task flows, URLs, and prepare micro-steps for browser automation",
            backstory=(
                "You are a specialist in validating government service tasks for browser automation. "
                "You carefully review task flows, validate URLs, and break down processes into "
                "micro-steps that can be reliably executed by browser automation tools. "
                "You ensure that all steps are complete, URLs are correct, and potential issues "
                "are identified and addressed before automation begins."
            ),
            llm=self.llm,
            memory=False,
            verbose=True,
            max_iter=10,
            max_execution_time=600
        )
    
    async def validate_task_flow(self, coordinator_instructions: str, 
                               intent_analysis: Dict[str, Any] = None,
                               research_results: Dict[str, Any] = None) -> ValidationResult:
        """
        Validate the task flow and prepare for automation.
        
        Args:
            coordinator_instructions: Instructions from coordinator agent
            intent_analysis: Intent analysis results
            research_results: Research results from coordinator
            
        Returns:
            ValidationResult with validation details and micro-steps
        """
        try:
            # Step 1: URL Validation
            url_validation_results = await self._validate_urls(research_results)
            
            # Step 2: Process Flow Validation
            flow_validation_results = await self._validate_process_flow(
                coordinator_instructions, intent_analysis, research_results
            )
            
            # Step 3: Generate Micro-Steps
            micro_steps = await self._generate_micro_steps(
                research_results, url_validation_results, flow_validation_results
            )
            
            # Step 4: Create Error Handling Plan
            error_handling_plan = await self._create_error_handling_plan(micro_steps)
            
            # Step 5: Create Monitoring Points
            monitoring_points = await self._create_monitoring_points(micro_steps)
            
            # Determine overall validation status
            validation_status = self._determine_validation_status(
                url_validation_results, flow_validation_results
            )
            
            # Create corrected flow if needed
            corrected_flow = self._create_corrected_flow(
                research_results, url_validation_results, flow_validation_results
            )
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                url_validation_results, flow_validation_results, micro_steps
            )
            
            return ValidationResult(
                validation_status=validation_status,
                corrected_flow=corrected_flow,
                confidence_score=confidence_score,
                validation_details=f"URL Validation: {url_validation_results}, Flow Validation: {flow_validation_results}",
                micro_steps=micro_steps,
                error_handling_plan=error_handling_plan,
                monitoring_points=monitoring_points
            )
            
        except Exception as e:
            logger.error(f"Task flow validation failed: {str(e)}")
            return ValidationResult(
                validation_status="failed",
                corrected_flow={},
                confidence_score=0.0,
                validation_details=f"Validation failed: {str(e)}",
                micro_steps=[],
                error_handling_plan=[],
                monitoring_points=[]
            )
    
    async def _validate_urls(self, research_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate URLs from research results."""
        if not research_results or not research_results.get('target_websites'):
            return {'status': 'no_urls', 'validated_urls': []}
        
        validated_urls = []
        for url in research_results['target_websites']:
            validation = self.url_validator.validate_government_url(url)
            validated_urls.append({
                'url': url,
                'validation': validation
            })
        
        valid_count = sum(1 for v in validated_urls if v['validation']['is_valid'])
        
        return {
            'status': 'completed',
            'total_urls': len(validated_urls),
            'valid_urls': valid_count,
            'validated_urls': validated_urls
        }
    
    async def _validate_process_flow(self, coordinator_instructions: str,
                                   intent_analysis: Dict[str, Any] = None,
                                   research_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate the process flow using LLM."""
        try:
            # Create validation prompt
            validation_prompt = f"""
You are validating a government service task flow for browser automation. Review the following:

COORDINATOR INSTRUCTIONS:
{coordinator_instructions}

INTENT ANALYSIS:
{intent_analysis}

RESEARCH RESULTS:
{research_results}

Validation Requirements:
1. **Process Completeness**: Are all necessary steps included?
2. **Logical Flow**: Do the steps follow a logical sequence?
3. **Missing Steps**: Are there any missing steps?
4. **Automation Feasibility**: Can these steps be automated?
5. **Error Scenarios**: What could go wrong?

Provide your validation in JSON format:
{{
    "process_complete": true/false,
    "logical_flow": true/false,
    "missing_steps": ["list of missing steps"],
    "automation_feasible": true/false,
    "error_scenarios": ["list of potential errors"],
    "recommendations": ["list of recommendations"],
    "confidence_score": 0.95
}}
"""
            
            # Create validation task
            validation_task = Task(
                description=validation_prompt,
                expected_output="JSON response with process flow validation results",
                agent=self.agent
            )
            
            # Execute validation
            validation_crew = Crew(
                agents=[self.agent],
                tasks=[validation_task],
                process=Process.sequential,
                verbose=True
            )
            
            result = validation_crew.kickoff()
            
            # Parse response
            return self._parse_validation_response(str(result))
            
        except Exception as e:
            logger.error(f"Process flow validation failed: {str(e)}")
            return {
                'process_complete': False,
                'logical_flow': False,
                'missing_steps': ['Validation failed'],
                'automation_feasible': False,
                'error_scenarios': [f'Validation error: {str(e)}'],
                'recommendations': ['Manual review required'],
                'confidence_score': 0.0
            }
    
    async def _generate_micro_steps(self, research_results: Dict[str, Any],
                                  url_validation: Dict[str, Any],
                                  flow_validation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate micro-steps for automation."""
        if not research_results or not research_results.get('process_steps'):
            return []
        
        # Use the micro-step generator
        process_steps = research_results['process_steps']
        target_website = research_results.get('target_websites', [''])[0] if research_results.get('target_websites') else ''
        
        micro_steps = self.step_generator.generate_micro_steps(process_steps, target_website)
        
        # Enhance with validation results
        for step in micro_steps:
            step['url_validation'] = url_validation
            step['flow_validation'] = flow_validation
        
        return micro_steps
    
    async def _create_error_handling_plan(self, micro_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create error handling plan for micro-steps."""
        error_handling_plan = []
        
        for step in micro_steps:
            error_plan = {
                'step_number': step['step_number'],
                'error_scenarios': [
                    'Element not found',
                    'Page not loaded',
                    'Authentication failed',
                    'Network timeout',
                    'Unexpected page content'
                ],
                'recovery_actions': [
                    'Wait and retry',
                    'Refresh page',
                    'Check credentials',
                    'Escalate to human',
                    'Alternative approach'
                ],
                'escalation_triggers': [
                    'Max retries exceeded',
                    'Critical failure',
                    'Authentication error',
                    'Unexpected behavior'
                ]
            }
            error_handling_plan.append(error_plan)
        
        return error_handling_plan
    
    async def _create_monitoring_points(self, micro_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create monitoring points for automation."""
        monitoring_points = []
        
        for step in micro_steps:
            monitoring_point = {
                'step_number': step['step_number'],
                'checkpoint': step['instruction'],
                'validation_criteria': step['validation_criteria'],
                'success_indicators': [
                    'Page loaded successfully',
                    'Element found and interacted with',
                    'Expected response received'
                ],
                'failure_indicators': [
                    'Page failed to load',
                    'Element not found',
                    'Unexpected error message',
                    'Authentication failure'
                ]
            }
            monitoring_points.append(monitoring_point)
        
        return monitoring_points
    
    def _determine_validation_status(self, url_validation: Dict[str, Any],
                                   flow_validation: Dict[str, Any]) -> str:
        """Determine overall validation status."""
        url_valid = url_validation.get('valid_urls', 0) > 0
        flow_valid = flow_validation.get('process_complete', False) and flow_validation.get('logical_flow', False)
        
        if url_valid and flow_valid:
            return 'passed'
        elif url_valid or flow_valid:
            return 'needs_correction'
        else:
            return 'failed'
    
    def _create_corrected_flow(self, research_results: Dict[str, Any],
                             url_validation: Dict[str, Any],
                             flow_validation: Dict[str, Any]) -> Dict[str, Any]:
        """Create corrected flow based on validation results."""
        corrected_flow = {
            'original_flow': research_results,
            'url_corrections': url_validation,
            'flow_corrections': flow_validation,
            'recommendations': flow_validation.get('recommendations', []),
            'corrected_steps': research_results.get('process_steps', [])
        }
        
        # Add missing steps if any
        missing_steps = flow_validation.get('missing_steps', [])
        if missing_steps:
            corrected_flow['corrected_steps'].extend(missing_steps)
        
        return corrected_flow
    
    def _calculate_confidence_score(self, url_validation: Dict[str, Any],
                                  flow_validation: Dict[str, Any],
                                  micro_steps: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence score."""
        url_score = 0.0
        if url_validation.get('total_urls', 0) > 0:
            url_score = url_validation.get('valid_urls', 0) / url_validation.get('total_urls', 1)
        
        flow_score = flow_validation.get('confidence_score', 0.0)
        
        steps_score = 0.8 if len(micro_steps) > 0 else 0.0
        
        # Weighted average
        confidence_score = (url_score * 0.3) + (flow_score * 0.5) + (steps_score * 0.2)
        
        return round(confidence_score, 2)
    
    def _parse_validation_response(self, response_text: str) -> Dict[str, Any]:
        """Parse validation response from JSON."""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                return self._fallback_parse_validation(response_text)
        except Exception as e:
            logger.error(f"Failed to parse validation response: {str(e)}")
            return self._fallback_parse_validation(response_text)
    
    def _fallback_parse_validation(self, response_text: str) -> Dict[str, Any]:
        """Fallback parsing for validation response."""
        return {
            'process_complete': False,
            'logical_flow': False,
            'missing_steps': ['Unable to parse validation'],
            'automation_feasible': False,
            'error_scenarios': ['Parsing failed'],
            'recommendations': ['Manual validation required'],
            'confidence_score': 0.0
        }


# Global validator agent instance
validator_agent = ValidatorAgent()
