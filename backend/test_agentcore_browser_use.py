"""
Enhanced test script for browser automation using browser_use with AWS Bedrock AgentCore.
Includes fallback mechanism: if remote browser fails, automatically falls back to local browser.
Based on AWS Bedrock AgentCore samples: getting_started-agentcore-browser-tool-with-browser-use.ipynb
"""

import asyncio
from browser_use import Agent, BrowserProfile, Browser
from browser_use.browser.session import BrowserSession
from langchain_aws import ChatBedrockConverse
from bedrock_agentcore.tools.browser_client import BrowserClient
from rich.console import Console
from contextlib import suppress
from boto3.session import Session
import os
from typing import Optional, Tuple
# Initialize console for rich output
console = Console()


async def setup_local_browser_fallback(region: str) -> Tuple[Browser, ChatBedrockConverse]:
    """
    Setup local browser as fallback when remote browser fails.
    
    Args:
        region: AWS region for Bedrock model
        
    Returns:
        Tuple of (Browser instance, Bedrock chat model)
    """
    console.print("[yellow]🔄 Setting up local browser fallback...[/yellow]")
    
    try:
        # Create local browser with optimized profile
        browser_profile = BrowserProfile(
            headless=False,  # Set to True for headless mode
            minimum_wait_page_load_time=0.5,
            wait_between_actions=0.3,
            keep_alive=True
        )
        
        # Initialize local browser
        local_browser = Browser(
            browser_profile=browser_profile,
            keep_alive=True
        )
        
        # Start local browser
        console.print("[cyan]🚀 Starting local browser...[/cyan]")
        await local_browser.start()
        
        # Create Bedrock chat model for local browser
        bedrock_chat = ChatBedrockConverse(
            model_id="apac.anthropic.claude-sonnet-4-20250514-v1:0",
            region_name=region
        )
        
        console.print("[green]✅ Local browser setup complete![/green]")
        return local_browser, bedrock_chat
        
    except Exception as e:
        console.print(f"[bold red]❌ Failed to setup local browser:[/bold red] {str(e)}")
        raise


async def run_browser_task(browser_session: BrowserSession, bedrock_chat: ChatBedrockConverse, task: str) -> None:
    """
    Run a browser automation task using browser_use
    
    Args:
        browser_session: Existing browser session to reuse
        bedrock_chat: Bedrock chat model instance
        task: Natural language task for the agent
    """
    try:
        # Show task execution
        console.print(f"\n[bold blue]🤖 Executing task:[/bold blue] {task}")
        
        # Create and run the agent
        agent = Agent(
            task=task,
            llm=bedrock_chat,
            browser_session=browser_session,
        )
        
        # Run with progress indicator
        with console.status("[bold green]Running browser automation...[/bold green]", spinner="dots"):
            await agent.run()
        
        console.print("[bold green]✅ Task completed successfully![/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error during task execution:[/bold red] {str(e)}")
        import traceback
        if console.is_terminal:
            traceback.print_exc()


async def run_tasks_with_fallback(browser_session: BrowserSession, bedrock_chat: ChatBedrockConverse, 
                                 tasks: list, region: str) -> None:
    """
    Run tasks with automatic fallback to local browser if remote fails.
    
    Args:
        browser_session: Remote browser session (can be None if fallback is used)
        bedrock_chat: Bedrock chat model instance
        tasks: List of tasks to execute
        region: AWS region for Bedrock model
    """
    local_browser = None
    current_browser_session = browser_session
    current_chat = bedrock_chat
    
    try:
        for i, task in enumerate(tasks, 1):
            console.print(f"\n[bold cyan]📋 Task {i}/{len(tasks)}[/bold cyan]")
            
            try:
                await run_browser_task(current_browser_session, current_chat, task)
                
            except Exception as e:
                console.print(f"[yellow]⚠️ Remote browser task failed:[/yellow] {str(e)}")
                
                # If this is the first failure and we haven't set up local browser yet
                if local_browser is None:
                    console.print("[yellow]🔄 Attempting fallback to local browser...[/yellow]")
                    
                    try:
                        local_browser, current_chat = await setup_local_browser_fallback(region)
                        current_browser_session = local_browser
                        
                        # Retry the failed task with local browser
                        console.print("[yellow]🔄 Retrying task with local browser...[/yellow]")
                        await run_browser_task(current_browser_session, current_chat, task)
                        
                    except Exception as fallback_error:
                        console.print(f"[bold red]❌ Local browser fallback also failed:[/bold red] {str(fallback_error)}")
                        console.print("[bold red]❌ Skipping this task and continuing...[/bold red]")
                        continue
                else:
                    console.print("[bold red]❌ Task failed with local browser, skipping...[/bold red]")
                    continue
                    
    finally:
        # Clean up local browser if it was created
        if local_browser:
            console.print("\n[yellow]🔌 Closing local browser...[/yellow]")
            try:
                await local_browser.kill()
                console.print("[green]✅ Local browser closed[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Error closing local browser:[/yellow] {str(e)}")


async def main():
    """Main function with fallback mechanism for browser automation."""
    console.print("[cyan]🚀 Starting AgentCore + browser_use Test with Fallback[/cyan]")
    
    # Setup the browser client
    boto_session = Session()
    region = "ap-southeast-2"  # Use consistent region for both browser and LLM
    console.print(f"[cyan]Using AWS region: {region}[/cyan]")
    
    # Define tasks to execute
    tasks = [
        "Search for a coffee maker on amazon.com and extract details of the first one",
        """Navigate to the JPJ (Road Transport Department) website at https://www.jpj.gov.my
        Look for the summons checking service (Semak Saman JPJ)
        Try to find a way to check summons using vehicle plate number JQM919
        If that's not available, try alternative government e-service platforms
        Provide a summary of what you found"""
    ]
    
    # Try to setup remote browser first
    browser_session = None
    bedrock_chat = None
    client = None
    
    try:
        console.print("[cyan]🌐 Attempting to setup remote browser...[/cyan]")
        
        # Setup the browser client
        client = BrowserClient(region)
        client.start()
        
        # Extract ws_url and headers
        ws_url, headers = client.generate_ws_headers()
        console.print(f"[cyan]WebSocket URL: {ws_url}[/cyan]")
        
        # Create browser profile with headers
        browser_profile = BrowserProfile(
            headers=headers,
            timeout=1500000,  # 150 seconds timeout
        )
        
        # Create a browser session with CDP URL and keep_alive=True for persistence
        browser_session = BrowserSession(
            cdp_url=ws_url,
            browser_profile=browser_profile,
            keep_alive=True  # Keep browser alive between tasks
        )
        
        # Initialize the browser session with retry logic
        console.print("[cyan]🔄 Initializing remote browser session...[/cyan]")
        
        # Wait for session to be fully ready (AWS timing issue)
        console.print("[yellow]⏳ Waiting for AWS session to be fully ready...[/yellow]")
        await asyncio.sleep(20)  # Wait 20 seconds for session to be ready
        
        # Validate session URL
        console.print(f"[cyan]Session URL: {ws_url}[/cyan]")
        console.print(f"[cyan]Session ID: {ws_url.split('/')[-2]}[/cyan]")
        
        max_retries = 3
        retry_delay = 10
        
        for attempt in range(max_retries):
            try:
                console.print(f"[cyan]🔄 Attempt {attempt + 1}/{max_retries} to connect to remote browser...[/cyan]")
                await browser_session.start()
                console.print("[green]✅ Successfully connected to remote browser session![/green]")
                break
            except Exception as e:
                if "404 Not Found" in str(e) or "Required resources not found" in str(e):
                    if attempt < max_retries - 1:
                        console.print(f"[yellow]⚠️ Remote session not ready yet, waiting {retry_delay} seconds before retry...[/yellow]")
                        await asyncio.sleep(retry_delay)
                        # Recreate browser session for retry
                        browser_session = BrowserSession(
                            cdp_url=ws_url,
                            browser_profile=browser_profile,
                            keep_alive=True
                        )
                    else:
                        console.print("[bold red]❌ All remote browser retry attempts failed.[/bold red]")
                        console.print("[yellow]💡 Remote session not available, will use local browser fallback.[/yellow]")
                        browser_session = None
                        break
                else:
                    console.print(f"[yellow]⚠️ Remote browser error:[/yellow] {str(e)}")
                    console.print("[yellow]💡 Will use local browser fallback.[/yellow]")
                    browser_session = None
                    break
        
        # Create ChatBedrockConverse for remote browser
        if browser_session:
            bedrock_chat = ChatBedrockConverse(
                model_id="apac.anthropic.claude-sonnet-4-20250514-v1:0",
                region_name=region
            )
            console.print("[green]✅ Remote browser session initialized and ready for tasks[/green]\n")
        else:
            console.print("[yellow]⚠️ Remote browser setup failed, will use local browser fallback[/yellow]")
            
    except Exception as e:
        console.print(f"[yellow]⚠️ Remote browser setup failed:[/yellow] {str(e)}")
        console.print("[yellow]💡 Will use local browser fallback.[/yellow]")
        browser_session = None
    
    # Run tasks with fallback mechanism
    try:
        if browser_session and bedrock_chat:
            console.print("[cyan]🌐 Running tasks with remote browser (with local fallback)[/cyan]")
            await run_tasks_with_fallback(browser_session, bedrock_chat, tasks, region)
        else:
            console.print("[cyan]🖥️ Running tasks with local browser only[/cyan]")
            # Setup local browser directly
            local_browser, local_chat = await setup_local_browser_fallback(region)
            await run_tasks_with_fallback(local_browser, local_chat, tasks, region)
            
    except Exception as e:
        console.print(f"[bold red]❌ Error during task execution:[/bold red] {str(e)}")
        raise
    finally:
        # Close the remote browser session if it was created
        if browser_session:
            console.print("\n[yellow]🔌 Closing remote browser session...[/yellow]")
            with suppress(Exception):
                await browser_session.close()
            console.print("[green]✅ Remote browser session closed[/green]")
        
        # Cleanup client
        if client:
            client.stop()
            console.print("Remote browser client stopped successfully!")


if __name__ == "__main__":
    # Run the test
    asyncio.run(main())