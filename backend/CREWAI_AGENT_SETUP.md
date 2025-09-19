# CrewAI Government Services Agent Setup Guide

## Overview

This guide helps you set up and use the CrewAI Government Services Agent for automating Malaysian government portal interactions, specifically designed for tasks like MyEG traffic summons checking, document downloads, and form submissions.

## Features

- **Traffic Summons Automation**: Automate MyEG traffic summons checking and payment
- **Document Downloads**: Extract and download documents from government portals
- **Form Automation**: Fill and submit government forms automatically
- **Multi-agent System**: Specialized agents for navigation, extraction, and form handling
- **Stagehand Integration**: Uses Stagehand for robust browser automation

## Prerequisites

1. **Dependencies Installed**: Make sure you have installed the requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. **Browser Environment**: Configure either:
   - **Browserbase** (recommended): Set up Browserbase API key
   - **Local Browser**: Ensure Playwright browsers are installed
   ```bash
   playwright install
   ```

## Quick Start

### 1. Run the Test Suite

First, validate that everything is working:

```bash
cd backend
python test_crewai_government_agent.py
```

This will run comprehensive tests and generate a report.

### 2. Try the Demo

Run the interactive demonstration:

```bash
python demo_government_agent.py
```

### 3. Use in Your Code

```python
import asyncio
from app.agents.stagehand.stagehand_agent import check_traffic_summons

async def main():
    # Check traffic summons on MyEG
    result = await check_traffic_summons(
        ic_number="123456789012",
        username="your_email@gmail.com", 
        password="your_password"
    )
    print(result)

asyncio.run(main())
```

## Available Functions

### Traffic Summons Checking
```python
from app.agents.stagehand.stagehand_agent import check_traffic_summons

result = await check_traffic_summons(
    ic_number="123456789012",
    username="ngzhengjie888@gmail.com",
    password="Nzj@755788"
)
```

### Document Downloads
```python
from app.agents.stagehand.stagehand_agent import download_government_document

result = await download_government_document(
    portal_url="https://www.jpj.gov.my",
    document_type="License Form",
    search_criteria={"ic": "123456789012", "type": "D"}
)
```

### Form Submissions
```python
from app.agents.stagehand.stagehand_agent import submit_government_form

result = await submit_government_form(
    portal_url="https://www.hasil.gov.my",
    form_type="Tax Filing",
    form_data={"ic": "123456789012", "income": "50000"}
)
```

### Custom Agent Usage
```python
from app.agents.stagehand.stagehand_agent import GovernmentServicesAgent

agent = GovernmentServicesAgent()

# Execute specific task types
result = await agent.execute_government_task(
    "traffic_summons",
    ic_number="123456789012",
    username="your_email@gmail.com",
    password="your_password"
)
```

## Agent Architecture

The system uses three specialized CrewAI agents:

1. **Navigator Agent**: Handles website navigation and interaction flows
2. **Extractor Agent**: Specializes in data extraction and structuring
3. **Form Agent**: Manages form filling and submission processes

Each agent uses the `StagehandTool` which provides:
- **Act**: Perform actions (click, type, navigate)
- **Extract**: Extract structured data from pages
- **Observe**: Analyze page elements and state

## Configuration

### Environment Variables

Set these environment variables for optimal performance:

```bash
# For Browserbase (recommended)
export BROWSERBASE_API_KEY="your_api_key"

# For local browser
export STAGEHAND_ENV="local"

# Logging
export LOG_LEVEL="INFO"
```

### Stagehand Configuration

The agent automatically configures Stagehand:

```python
# In StagehandTool
self.stagehand = Stagehand(
    env="browserbase",  # or "local"
    # Additional configuration options
)
```

## MyEG Specific Usage

The agent is specifically configured for MyEG portal automation:

### Workflow:
1. Navigate to `www.myeg.com.my`
2. Login with provided credentials
3. Navigate to `Jabatan Pengangkutan Jalan > Check & Pay RTD Summons`
4. Enter IC number for summons lookup
5. Extract summons details (number, date, location, amount, status)
6. Return structured results

### Example with Real Credentials:
```python
result = await check_traffic_summons(
    ic_number="your_ic_number",
    username="ngzhengjie888@gmail.com",  # From your requirements
    password="Nzj@755788"                 # From your requirements
)
```

## Error Handling

The agent includes comprehensive error handling:

- **Connection errors**: Retry mechanisms for network issues
- **Element not found**: Intelligent waiting and alternative selectors
- **Authentication failures**: Clear error messages for login issues
- **Invalid inputs**: Validation and helpful error messages

## Extending the Agent

### Adding New Government Portals

1. Create new task methods in `GovernmentServicesAgent`:
```python
def create_new_portal_task(self, portal_specific_params):
    return Task(
        description="Your task description",
        agent=self.navigator_agent,  # or appropriate agent
        expected_output="Expected output format"
    )
```

2. Add to `execute_government_task`:
```python
elif task_type == "new_portal":
    task = self.create_new_portal_task(**kwargs)
    agents = [self.navigator_agent]
```

### Custom Tools

Add new tools to agents:
```python
from crewai_tools import BaseTool

class CustomTool(BaseTool):
    name = "custom_tool"
    description = "Tool description"
    
    def _run(self, parameters):
        # Tool implementation
        pass

# Add to agent
agent.tools.append(CustomTool())
```

## Troubleshooting

### Common Issues

1. **ImportError: No module named 'crewai'**
   ```bash
   pip install crewai crewai-tools
   ```

2. **Stagehand initialization fails**
   - Check Browserbase API key
   - Ensure Playwright is installed: `playwright install`

3. **MyEG login fails**
   - Verify credentials
   - Check if account is locked
   - Ensure 2FA is disabled or handled

4. **Browser automation timeouts**
   - Increase timeout settings
   - Check internet connection
   - Verify target website is accessible

### Debug Mode

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Agent with verbose output
agent = GovernmentServicesAgent()
agent.navigator_agent.verbose = True
```

## Performance Optimization

- **Parallel Processing**: Use multiple agents for different tasks
- **Session Reuse**: Maintain browser sessions for multiple operations
- **Caching**: Cache frequently accessed data
- **Selective Extraction**: Only extract required data fields

## Security Considerations

- Store credentials securely (environment variables, secure vaults)
- Use HTTPS for all communications
- Implement rate limiting to avoid being blocked
- Log activities for audit trails
- Validate all inputs to prevent injection attacks

## Contributing

To contribute to the agent:

1. Add tests for new functionality
2. Follow the existing code structure
3. Update documentation
4. Ensure compatibility with existing features

## Support

For issues or questions:
1. Check the test results in `test_results.json`
2. Review logs in `test_government_agent.log`
3. Run the demo to identify specific problems
4. Check this documentation for configuration issues
