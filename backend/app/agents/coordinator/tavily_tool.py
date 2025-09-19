"""
Tavily search tool for government service research.
"""

from typing import Dict, Any, List, Optional
from crewai.tools import BaseTool
from tavily import TavilyClient
import os
from app.core.logging import get_logger
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()
logger = get_logger(__name__)


class TavilySearchTool(BaseTool):
    """Tavily search tool for researching government services and processes."""
    
    name: str = "tavily_search"
    description: str = (
        "Search the web for information about Malaysian government services, "
        "including transportation services, business renewals, tax services, "
        "license renewals, and other government e-services. Use this to find "
        "the exact steps and requirements for any government process."
    )
    
    # Pydantic fields for the tool
    tavily_client: Optional[TavilyClient] = Field(default=None, exclude=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Tavily client with API key."""
        try:
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                logger.warning("TAVILY_API_KEY not found in environment variables")
                return
            
            self.tavily_client = TavilyClient(api_key=api_key)
            logger.info("Tavily client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Tavily client: {str(e)}")
    
    def _run(self, query: str, **kwargs) -> str:
        """
        Execute Tavily search query.
        
        Args:
            query: Search query string
            **kwargs: Additional parameters for search
            
        Returns:
            Search results as formatted string
        """
        if not self.tavily_client:
            return "Error: Tavily client not initialized. Please check TAVILY_API_KEY."
        
        try:
            # Perform search with specific parameters for government services
            search_params = {
                "query": query,
                "search_depth": "advanced",
                "include_answer": True,
                "include_raw_content": False,
                "max_results": 5,
                "include_domains": [
                    "jpj.gov.my",
                    "myeg.com.my", 
                    "hasil.gov.my",
                    "jpn.gov.my",
                    "kwsp.gov.my",
                    "gov.my"
                ],
                "exclude_domains": [
                    "facebook.com",
                    "twitter.com", 
                    "instagram.com",
                    "youtube.com"
                ]
            }
            
            # Add any additional parameters from kwargs
            search_params.update(kwargs)
            
            logger.info(f"Executing Tavily search: {query}")
            response = self.tavily_client.search(**search_params)
            
            # Format the response
            return self._format_search_results(response)
            
        except Exception as e:
            logger.error(f"Tavily search failed: {str(e)}")
            return f"Search failed: {str(e)}"
    
    def _format_search_results(self, response: Dict[str, Any]) -> str:
        """
        Format Tavily search results into a readable string.
        
        Args:
            response: Raw Tavily API response
            
        Returns:
            Formatted search results
        """
        try:
            formatted_results = []
            
            # Add answer if available
            if response.get("answer"):
                formatted_results.append(f"Answer: {response['answer']}")
                formatted_results.append("")
            
            # Add search results
            results = response.get("results", [])
            if results:
                formatted_results.append("Search Results:")
                formatted_results.append("=" * 50)
                
                for i, result in enumerate(results[:5], 1):  # Limit to top 5 results
                    title = result.get("title", "No title")
                    url = result.get("url", "No URL")
                    content = result.get("content", "No content")
                    
                    formatted_results.append(f"{i}. {title}")
                    formatted_results.append(f"   URL: {url}")
                    formatted_results.append(f"   Content: {content[:200]}...")
                    formatted_results.append("")
            
            return "\n".join(formatted_results)
            
        except Exception as e:
            logger.error(f"Failed to format search results: {str(e)}")
            return f"Error formatting results: {str(e)}"
    
    def search_government_service(self, service_type: str, specific_query: str = "") -> str:
        """
        Search specifically for Malaysian government service information.
        
        Args:
            service_type: Type of government service (e.g., "business renewal", "tax filing", "license renewal")
            specific_query: Specific search query
            
        Returns:
            Formatted search results
        """
        # Construct specific query for government services
        query = f"Malaysia {service_type} process requirements"
        if specific_query:
            query += f" {specific_query}"
        
        # Add specific terms to improve government service results
        query += " site:gov.my OR site:myeg.com.my OR site:jpj.gov.my OR site:hasil.gov.my OR site:jpn.gov.my OR site:kwsp.gov.my"
        
        return self._run(query)
    
    def search_malaysian_government_process(self, user_message: str) -> str:
        """
        Search for any Malaysian government service process based on user message.
        
        Args:
            user_message: User's request message
            
        Returns:
            Formatted search results about the government service
        """
        # Extract key terms from user message
        query = f"Malaysia government service {user_message} process requirements"
        
        # Add government website domains
        query += " site:gov.my OR site:myeg.com.my OR site:jpj.gov.my OR site:hasil.gov.my OR site:jpn.gov.my OR site:kwsp.gov.my OR site:ssm.com.my"
        
        return self._run(query)
