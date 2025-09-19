# CrewAI + Stagehand Environment Setup Guide

## Required Environment Variables

Based on the Context7 documentation, you need to set up the following environment variables for the CrewAI Government Services Agent to work properly:

### 1. Browserbase Configuration (Recommended for Production)

```bash
# Get these from your Browserbase dashboard: https://www.browserbase.com/
BROWSERBASE_API_KEY="your-browserbase-api-key"
BROWSERBASE_PROJECT_ID="your-browserbase-project-id"
```

### 2. LLM API Configuration (Choose ONE)

**Option A: OpenAI (Recommended)**
```bash
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY="your-openai-api-key"
```

**Option B: Anthropic**
```bash
# Get from: https://console.anthropic.com/
ANTHROPIC_API_KEY="your-anthropic-api-key"
```

### 3. Environment Setup

Create a `.env` file in your backend directory:

```bash
# Copy this to backend/.env and fill in your actual keys

# Browserbase (for cloud browser automation)
BROWSERBASE_API_KEY=your-browserbase-api-key-here
BROWSERBASE_PROJECT_ID=your-browserbase-project-id-here

# LLM Provider (choose one)
OPENAI_API_KEY=your-openai-api-key-here
# ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Optional: Local browser testing (if not using Browserbase)
# LOCAL_BROWSER=true
```

### 4. Install Additional Dependencies

Make sure you have installed the correct versions:

```bash
pip install stagehand-py crewai crewai-tools python-dotenv
```

### 5. Verify Setup

Test your configuration by running:

```python
# Test script to verify environment
import os
from dotenv import load_dotenv

load_dotenv()

# Check required variables
required_vars = {
    'LLM': os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"),
    'BROWSERBASE_API_KEY': os.environ.get("BROWSERBASE_API_KEY"),
    'BROWSERBASE_PROJECT_ID': os.environ.get("BROWSERBASE_PROJECT_ID")
}

for var_name, var_value in required_vars.items():
    status = "✅ SET" if var_value else "❌ MISSING"
    print(f"{var_name}: {status}")

if all(required_vars.values()):
    print("\n🎉 All required environment variables are configured!")
else:
    print("\n⚠️  Please set missing environment variables before running the agent.")
```

## Usage Notes

1. **Browserbase vs Local**: The agent will automatically use local browser if Browserbase keys are not provided
2. **Model Selection**: The agent will use GPT-4o if OpenAI key is provided, otherwise Claude 3.5 Sonnet
3. **Error Handling**: The agent includes automatic retry and error recovery mechanisms
4. **Logging**: Set verbose levels in the environment for debugging

## Example Working Configuration

```bash
# Example .env file that works
BROWSERBASE_API_KEY=bb_1234567890abcdef
BROWSERBASE_PROJECT_ID=proj_abcdef123456
OPENAI_API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz
```

This configuration will enable the full functionality of the CrewAI Government Services Agent with browser automation capabilities.
