# 3-Agent Architecture Plan for Malaysian Government Services

## Executive Summary

This document outlines the implementation plan for a sophisticated 3-agent architecture designed to handle Malaysian government service requests with dynamic intent detection, intelligent task validation, and step-by-step browser automation using Nova Act with AWS Bedrock AgentCore Browser.

## Architecture Overview

```
User Request → Coordinator Agent → Validator Agent → Automation Agent → Nova Act → Browser
                ↓                    ↓                    ↓
            Intent Detection    Task Validation    Micro-step Execution
            Tavily Research     URL Validation     Error Handling
            Credential Check    Flow Correction    Human Intervention
```

## Agent 1: Coordinator Agent (Enhanced)

### Primary Responsibilities
1. **Dynamic Intent Detection** (Chain-of-Thought Prompting)
2. **Research & Information Gathering** (Tavily Integration)
3. **Credential Management** (User Interaction)
4. **Task Orchestration** (Delegation to Validator)

### Implementation Details

#### Intent Detection Strategy
- **No Predefined Categories**: Use advanced prompting techniques for dynamic intent detection
- **Chain-of-Thought Prompting**: Guide the agent to think step-by-step about user intent
- **Context-Aware Analysis**: Consider conversation history and user entity memory

```python
# Example Prompting Strategy
intent_detection_prompt = """
You are analyzing a user request for Malaysian government services. Think step by step:

1. What is the user trying to accomplish?
2. What type of government service is involved?
3. What information or credentials might be needed?
4. Is this a payment, inquiry, registration, or other type of request?
5. What websites or portals might be involved?

Based on your analysis, provide:
- Intent classification (payment, inquiry, registration, etc.)
- Required research areas
- Missing information needed from user
- Recommended next steps
"""
```

#### Memory Integration (AgentScope + AWS)
- **Short-Term Memory**: Session-specific context using AgentScope's InMemoryMemory
- **Long-Term Memory**: Cross-session learnings using Mem0LongTermMemory with AWS DynamoDB
- **Entity Memory**: User-specific preferences and service history

```python
# Memory Configuration
memory_config = {
    "short_term": InMemoryMemory(),  # AgentScope built-in
    "long_term": Mem0LongTermMemory(
        agent_name="coordinator",
        user_name=user_id,
        vector_store=VectorStoreConfig(
            provider="dynamodb",
            config={"table_name": "agent-memory"}
        )
    ),
    "entity_memory": EntityMemory(
        storage_backend="dynamodb",
        table_name="user-entities"
    )
}
```

#### Tavily Integration
- Research government service procedures
- Validate official website URLs
- Gather step-by-step process information
- Identify required credentials and information

### Output Format
```json
{
    "intent": "payment_intent",
    "service_type": "rtd_summons_payment",
    "research_results": {
        "target_website": "https://www.myeg.com.my",
        "process_steps": ["login", "navigate_to_summons", "enter_details", "payment"],
        "required_credentials": ["email", "password"],
        "required_information": ["ic_number", "summons_reference"]
    },
    "missing_information": ["user_credentials"],
    "next_agent": "validator",
    "confidence_score": 0.95
}
```

## Agent 2: Validator Agent (New)

### Primary Responsibilities
1. **Task Flow Validation**
2. **URL & Process Verification**
3. **Micro-Step Breakdown**
4. **Error Prevention & Correction**

### Implementation Details

#### Validation Logic
```python
validation_criteria = {
    "url_validation": {
        "check_ssl": True,
        "verify_domain": True,
        "check_government_domains": True,
        "validate_service_path": True
    },
    "process_validation": {
        "step_completeness": True,
        "logical_flow": True,
        "credential_requirements": True,
        "error_scenarios": True
    },
    "nova_act_readiness": {
        "micro_step_breakdown": True,
        "clear_instructions": True,
        "error_handling_plan": True
    }
}
```

#### Micro-Step Generation
Break down tasks into granular steps for Nova Act:

```python
# Example Micro-Steps for RTD Summons Payment
micro_steps = [
    {
        "step": 1,
        "action": "navigate",
        "target": "https://www.myeg.com.my",
        "instruction": "Go to MyEG website homepage",
        "validation": "verify_page_loaded"
    },
    {
        "step": 2,
        "action": "login",
        "target": "login_form",
        "instruction": "Click on login button and enter credentials",
        "validation": "verify_login_success"
    },
    {
        "step": 3,
        "action": "navigate",
        "target": "jpj_section",
        "instruction": "Navigate to JPJ > Check & Pay RTD Summons",
        "validation": "verify_navigation_success"
    },
    # ... more steps
]
```

#### Error Prevention
- Pre-validate all URLs and processes
- Identify potential "black holes" or error scenarios
- Create fallback plans for common failures
- Set up monitoring points for each step

### Output Format
```json
{
    "validation_status": "passed",
    "corrected_flow": {
        "target_website": "https://www.myeg.com.my",
        "micro_steps": [...],
        "error_handling_plan": [...],
        "monitoring_points": [...]
    },
    "confidence_score": 0.98,
    "next_agent": "automation"
}
```

## Agent 3: Automation Agent (Enhanced)

### Primary Responsibilities
1. **Nova Act Orchestration** (Step-by-step guidance)
2. **Error Detection & Recovery**
3. **Human Intervention Escalation**
4. **Real-time Monitoring**

### Implementation Details

#### Nova Act Integration Strategy
```python
class NovaActOrchestrator:
    def __init__(self):
        self.browser_client = BrowserClient(region="us-east-1")
        self.nova_act = None
        self.current_step = 0
        self.error_count = 0
        self.max_errors = 3
    
    async def execute_micro_step(self, step: dict):
        """Execute a single micro-step with error handling"""
        try:
            # Execute the step
            result = await self.nova_act.act(step["instruction"])
            
            # Validate the result
            if self.validate_step_result(result, step):
                return {"status": "success", "result": result}
            else:
                return await self.handle_step_failure(step, result)
                
        except Exception as e:
            return await self.handle_step_error(step, e)
    
    async def handle_step_failure(self, step: dict, result):
        """Handle step failure with intelligent recovery"""
        self.error_count += 1
        
        if self.error_count < self.max_errors:
            # Try alternative approach
            return await self.retry_with_modification(step)
        else:
            # Escalate to human intervention
            return await self.escalate_to_human(step, result)
```

#### Error Handling & Recovery
```python
error_recovery_strategies = {
    "login_failed": {
        "detection": "check for login error messages",
        "recovery": "verify credentials and retry",
        "escalation": "ask user for correct credentials"
    },
    "page_not_found": {
        "detection": "check for 404 or navigation errors",
        "recovery": "try alternative navigation path",
        "escalation": "manual navigation assistance"
    },
    "captcha_detected": {
        "detection": "check for captcha elements",
        "recovery": "pause and wait for human input",
        "escalation": "human captcha solving"
    },
    "payment_error": {
        "detection": "check for payment failure messages",
        "recovery": "verify payment details",
        "escalation": "manual payment assistance"
    }
}
```

#### Human Intervention Integration
```python
async def escalate_to_human(self, step: dict, error_context: dict):
    """Escalate to human intervention with context"""
    intervention_request = {
        "step_failed": step,
        "error_context": error_context,
        "browser_state": await self.get_browser_state(),
        "user_context": self.user_context,
        "suggested_actions": self.generate_suggestions(step, error_context)
    }
    
    # Notify human operator
    await self.notify_human_operator(intervention_request)
    
    # Wait for human intervention
    return await self.wait_for_human_response()
```

### Output Format
```json
{
    "execution_status": "completed|failed|human_intervention_required",
    "completed_steps": [...],
    "failed_step": {...},
    "error_details": {...},
    "human_intervention": {
        "required": true,
        "context": {...},
        "suggested_actions": [...]
    }
}
```

## Memory Management Strategy

### Multi-Layer Memory Architecture

#### 1. Short-Term Memory (AgentScope InMemoryMemory)
- Current session context
- Recent conversation history
- Temporary task state
- Immediate user preferences

#### 2. Long-Term Memory (Mem0LongTermMemory + AWS DynamoDB)
- Cross-session learnings
- Service process improvements
- Error pattern recognition
- User behavior patterns

#### 3. Entity Memory (Custom AWS DynamoDB)
- User-specific data
- Service preferences
- Credential templates (encrypted)
- Service history

### Memory Integration Points
```python
class MemoryManager:
    def __init__(self):
        self.short_term = InMemoryMemory()
        self.long_term = Mem0LongTermMemory(...)
        self.entity = EntityMemory(...)
    
    async def get_context(self, user_id: str, session_id: str):
        """Get comprehensive context for decision making"""
        return {
            "short_term": await self.short_term.get(session_id),
            "long_term": await self.long_term.get(user_id),
            "entity": await self.entity.get(user_id),
            "conversation_history": await self.get_conversation_history(session_id)
        }
    
    async def update_memory(self, user_id: str, session_id: str, 
                          interaction_data: dict):
        """Update all memory layers with interaction data"""
        await self.short_term.store(session_id, interaction_data)
        await self.long_term.store(user_id, interaction_data)
        await self.entity.update(user_id, interaction_data)
```

## Human Intervention Protocol

### Escalation Triggers
1. **Authentication Failures** (3+ attempts)
2. **Navigation Errors** (unable to find elements)
3. **Payment Failures** (transaction errors)
4. **Captcha Detection** (automated solving failed)
5. **Unexpected Website Changes** (structure modified)

### Intervention Workflow
```python
class HumanInterventionManager:
    async def handle_intervention_request(self, request: dict):
        """Process human intervention request"""
        # 1. Analyze the failure context
        analysis = await self.analyze_failure_context(request)
        
        # 2. Generate intervention options
        options = await self.generate_intervention_options(analysis)
        
        # 3. Present to human operator
        human_decision = await self.present_to_human(options)
        
        # 4. Execute human decision
        result = await self.execute_human_decision(human_decision)
        
        # 5. Update memory with learning
        await self.update_memory_with_learning(request, result)
        
        return result
```

### Human Operator Interface
- Real-time browser viewing
- Step-by-step guidance
- Error context display
- Suggested actions
- Manual override capabilities

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
1. Enhance Coordinator Agent with chain-of-thought prompting
2. Implement basic Tavily integration
3. Set up AgentScope memory components
4. Create Validator Agent skeleton

### Phase 2: Validation & Breakdown (Week 3-4)
1. Implement Validator Agent logic
2. Create micro-step generation algorithms
3. Build URL and process validation
4. Test validation accuracy

### Phase 3: Automation Enhancement (Week 5-6)
1. Enhance Automation Agent with Nova Act orchestration
2. Implement error handling and recovery
3. Build human intervention framework
4. Create monitoring and logging

### Phase 4: Memory Integration (Week 7-8)
1. Integrate Mem0LongTermMemory with AWS
2. Set up entity memory system
3. Implement cross-session learning
4. Test memory persistence

### Phase 5: Testing & Optimization (Week 9-10)
1. End-to-end testing with government services
2. Performance optimization
3. Error handling refinement
4. Human intervention testing

## Technical Requirements

### Dependencies
```python
# Core Framework
crewai>=0.28.0
agentscope>=0.2.0
nova-act>=1.0.0
bedrock-agentcore>=1.0.0

# Memory Management
mem0ai>=0.1.0
chromadb>=0.4.0

# AWS Integration
boto3>=1.34.0
dynamodb-local>=0.1.0

# Research & Validation
tavily-python>=0.3.0
requests>=2.31.0
beautifulsoup4>=4.12.0

# Browser Automation
playwright>=1.54.0
selenium>=4.15.0
```

### AWS Services Required
- **DynamoDB**: Entity memory and conversation history
- **Bedrock AgentCore**: Browser automation platform
- **Lambda**: Serverless function execution
- **S3**: Log storage and backup
- **CloudWatch**: Monitoring and logging

### Environment Variables
```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1

# Agent Configuration
NOVA_ACT_API_KEY=your_nova_act_key
TAVILY_API_KEY=your_tavily_key

# Memory Configuration
MEM0_API_KEY=your_mem0_key
DYNAMODB_TABLE_PREFIX=ai4ai

# Browser Configuration
BROWSER_HEADLESS=false
BROWSER_TIMEOUT=30
```

## Success Metrics

### Functional Metrics
- **Intent Detection Accuracy**: >95%
- **Task Completion Rate**: >90%
- **Error Recovery Rate**: >85%
- **Human Intervention Rate**: <10%

### Performance Metrics
- **Average Task Completion Time**: <5 minutes
- **Memory Retrieval Speed**: <2 seconds
- **Browser Automation Success Rate**: >95%
- **System Uptime**: >99%

### User Experience Metrics
- **User Satisfaction Score**: >4.5/5
- **Task Success Rate**: >90%
- **Error Resolution Time**: <2 minutes
- **Human Intervention Response Time**: <30 seconds

## Risk Mitigation

### Technical Risks
1. **Nova Act Reliability**: Implement fallback to manual browser automation
2. **Memory Performance**: Use caching and optimization strategies
3. **AWS Service Limits**: Implement rate limiting and retry logic
4. **Browser Compatibility**: Test across multiple browser versions

### Business Risks
1. **Government Website Changes**: Implement adaptive validation
2. **Security Concerns**: Use encrypted credential storage
3. **Compliance Issues**: Implement audit logging and data protection
4. **Scalability Limits**: Design for horizontal scaling

## Conclusion

This 3-agent architecture provides a robust, scalable solution for Malaysian government service automation with intelligent error handling, comprehensive memory management, and seamless human intervention capabilities. The implementation follows best practices for agent orchestration, memory management, and browser automation while maintaining security and compliance standards.

The phased implementation approach ensures steady progress with continuous testing and validation, ultimately delivering a production-ready system capable of handling complex government service requests with high reliability and user satisfaction.
