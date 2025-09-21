
# from strands import Agent
# from strands_tools.browser import AgentCoreBrowser
# import os
# from dotenv import load_dotenv
# load_dotenv()
# import logging


# def create_agent():
#     """Create and configure the Strands agent with AgentCoreBrowser"""
    
#     agent_core_browser = AgentCoreBrowser(region="us-east-1")
#     agent = Agent(
#         tools=[agent_core_browser.browser],
#         model="amazon.nova-lite-v1:0",  # Correct for us-east-1 (with us. prefix)
#     )
#     return agent
    
# # Initialize agent globally
# strands_agent = create_agent()  

# def invoke(payload):
#     user_message = payload.get("prompt", "")
#     response = strands_agent(user_message)
#     return response.message["content"][0]["text"]

# if __name__ == "__main__":
#     response = invoke(
#         {
#             "prompt": "Search for macbooks on amazon.com and get the details of the first result"
#         }
#     )

