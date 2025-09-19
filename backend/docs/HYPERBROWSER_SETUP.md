# HyperBrowser Setup Guide

This guide explains how to set up HyperBrowser for remote browser automation in your AI4AI project.

## What is HyperBrowser?

HyperBrowser is a cloud-based browser automation platform that provides:
- Remote browser instances in the cloud
- Anti-detection features (stealth mode, proxy rotation)
- Automatic captcha solving
- WebSocket/CDP connections for browser automation

## Getting Started

### 1. Get API Key

1. Go to [HyperBrowser.ai](https://hyperbrowser.ai)
2. Sign up for an account
3. Navigate to your dashboard
4. Copy your API key

### 2. Environment Configuration

Add your HyperBrowser API key to your `.env` file:

```bash
# HyperBrowser Configuration
HYPERBROWSER_API_KEY=your_hyperbrowser_api_key_here
```

### 3. Understanding CDP URL vs Direct API

HyperBrowser provides two ways to connect:

#### Option A: Direct API (Recommended)
The automation agent automatically creates HyperBrowser sessions using the Python SDK. No additional configuration needed.

```python
# This happens automatically in automation_agent.py
from hyperbrowser import AsyncHyperbrowser

client = AsyncHyperbrowser(api_key=os.getenv('HYPERBROWSER_API_KEY'))
session = await client.sessions.create()
```

#### Option B: Manual CDP URL (Advanced)
If you want to use a specific CDP endpoint, you can set:

```bash
# Manual CDP URL (optional)
REMOTE_BROWSER_CDP_URL=wss://your-hyperbrowser-session.hyperbrowser.ai
```

## Session Configuration

The automation agent creates HyperBrowser sessions with these settings:

```python
session_params = CreateSessionParams(
    use_proxy=True,          # Use proxy for anonymity
    proxy_country="US",      # Set proxy country
    use_stealth=True,        # Enable stealth mode
    solve_captchas=True,     # Auto-solve captchas
    adblock=True            # Block ads for faster loading
)
```

## How It Works

1. **Session Creation**: When automation starts, a new HyperBrowser session is created
2. **WebSocket Connection**: Browser-Use connects to HyperBrowser via WebSocket
3. **Automation**: Your AI agent controls the remote browser
4. **Cleanup**: Session is automatically destroyed when done

## Architecture Flow

```
AI Agent (Browser-Use) 
    ↓ WebSocket/CDP
HyperBrowser Cloud Session
    ↓ Proxy/Stealth
Target Website (e.g., JPJ, LHDN)
```

## Session Management

### Automatic Session Management
The automation agent handles sessions automatically:

```python
# Session created when browser initializes
await self._initialize_hyperbrowser()

# Session destroyed when automation completes  
await self._cleanup_hyperbrowser_session()
```

### Manual Session Control (Advanced)

If you need manual control:

```python
from hyperbrowser import AsyncHyperbrowser

# Create client
client = AsyncHyperbrowser(api_key="your_api_key")

# Create session
session = await client.sessions.create()
print(f"Session ID: {session.id}")
print(f"WebSocket URL: {session.ws_endpoint}")

# Use with Browser-Use
browser = Browser(cdp_url=session.ws_endpoint)

# Clean up
await client.sessions.stop(session.id)
```

## Configuration Options

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `HYPERBROWSER_API_KEY` | Your HyperBrowser API key | ✅ Yes | None |
| `REMOTE_BROWSER_CDP_URL` | Manual CDP URL (optional) | ❌ No | Auto-generated |

### Session Parameters

You can customize session creation by modifying `automation_agent.py`:

```python
session_params = CreateSessionParams(
    use_proxy=True,                    # Enable proxy
    proxy_country="MY",                # Malaysia proxy for local sites
    use_stealth=True,                  # Stealth mode
    solve_captchas=True,               # Auto-solve captchas
    adblock=True,                      # Block ads
    screen_width=1920,                 # Screen resolution
    screen_height=1080,
    timezone="Asia/Kuala_Lumpur",      # Malaysia timezone
    language="en-US,en;q=0.9",         # Language preferences
)
```

## Troubleshooting

### Common Issues

1. **"Failed to initialize HyperBrowser"**
   - Check your API key is correct
   - Verify your account has credits
   - Check internet connection

2. **"WebSocket connection failed"**
   - HyperBrowser session might have expired
   - Check if session was properly created
   - Try recreating the session

3. **"Browser automation timing out"**
   - Increase timeout values in automation agent
   - Check if target website is accessible
   - Verify proxy settings

### Debug Mode

Enable debug logging to see HyperBrowser session details:

```python
import logging
logging.getLogger("hyperbrowser").setLevel(logging.DEBUG)
```

### Session Monitoring

Monitor your HyperBrowser sessions:

```python
# Check active sessions
sessions = await client.sessions.list()
for session in sessions:
    print(f"Session {session.id}: {session.status}")

# Get session details
session_detail = await client.sessions.get(session_id)
print(f"WebSocket: {session_detail.ws_endpoint}")
```

## Best Practices

### 1. Session Lifecycle
- Create sessions only when needed
- Always clean up sessions after use
- Handle session timeouts gracefully

### 2. Error Handling
```python
try:
    session = await client.sessions.create()
    # Use session...
except Exception as e:
    logger.error(f"HyperBrowser session failed: {e}")
    # Fallback to local browser
finally:
    await client.sessions.stop(session.id)
```

### 3. Resource Management
- Don't create multiple sessions unnecessarily
- Monitor your usage/credits
- Use appropriate session parameters for your use case

### 4. Malaysia-Specific Settings
For Malaysian government sites, consider:

```python
session_params = CreateSessionParams(
    proxy_country="MY",                # Malaysia proxy
    timezone="Asia/Kuala_Lumpur",      # Local timezone
    language="en-US,ms-MY",            # English + Malay
    use_stealth=True,                  # Avoid detection
)
```

## Integration with Human-in-the-Loop

HyperBrowser works seamlessly with the human-in-the-loop system:

1. **Session Sharing**: Same browser session is used for both automated and human-guided steps
2. **State Persistence**: Browser state (cookies, login) persists across interventions
3. **Real-time Monitoring**: Frontend can observe browser actions via WebSocket

## Cost Optimization

### Tips to Reduce Costs
1. **Session Reuse**: Keep sessions alive for multiple related tasks
2. **Efficient Timing**: Don't create sessions too early
3. **Quick Cleanup**: Destroy sessions immediately after completion
4. **Local Fallback**: Use local browser for testing/development

### Session Duration
- Sessions auto-expire after inactivity
- Typical session duration: 5-30 minutes depending on task
- Monitor usage in HyperBrowser dashboard

## Security Considerations

### Data Privacy
- HyperBrowser sessions are isolated
- No persistent data storage in cloud browsers
- Sessions are destroyed after use

### API Key Security
```bash
# Never commit API keys to git
echo "HYPERBROWSER_API_KEY" >> .gitignore

# Use environment variables
export HYPERBROWSER_API_KEY="your_key_here"

# Or use .env files (not committed)
HYPERBROWSER_API_KEY=your_key_here
```

## Support

- **HyperBrowser Documentation**: https://docs.hyperbrowser.ai
- **API Reference**: https://docs.hyperbrowser.ai/reference
- **Support**: Contact HyperBrowser support for API issues
- **Project Issues**: Create GitHub issues for integration problems

## Example: Complete Flow

Here's how a complete automation flow works with HyperBrowser:

```python
# 1. User requests vehicle summons check
user_message = "Check if there are any summons for my vehicle WAA1234"

# 2. Coordinator processes request
coordinator_result = await coordinator_agent.process_user_request(
    user_message, 
    {"plate_number": "WAA1234", "ic_number": "123456-78-9012"}
)

# 3. If automation needed, coordinator calls automation agent
if coordinator_result["status"] == "ready_for_automation":
    # 4. Automation agent creates HyperBrowser session
    session = await hyperbrowser_client.sessions.create(session_params)
    
    # 5. Browser-Use connects to HyperBrowser
    browser = Browser(cdp_url=session.ws_endpoint)
    
    # 6. AI agent navigates to JPJ website
    agent = BrowserAgent(
        task="Check vehicle summons for WAA1234",
        llm=llm,
        browser=browser,
        tools=human_tools  # Includes human-in-the-loop tools
    )
    
    # 7. If human input needed (login credentials), WebSocket requests it
    result = await agent.run()
    
    # 8. Session cleaned up automatically
    await hyperbrowser_client.sessions.stop(session.id)
```

This setup provides a robust, scalable browser automation solution with human-in-the-loop capabilities for Malaysian government services.
