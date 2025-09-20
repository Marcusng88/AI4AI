"""Application configuration settings."""

from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "AI-Enhanced Government Services"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # AWS
    aws_region: Optional[str] = os.getenv("DEFAULT_AWS_REGION", "ap-southeast-5")
    aws_access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    # DynamoDB
    dynamodb_chat_sessions_table: str = "ai4ai-chat-sessions"
    dynamodb_chat_messages_table: str = "ai4ai-chat-messages"

    # Bedrock Configuration (ap-southeast-2 because ap-southeast-5 doesn't support Bedrock)
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_region: str = "ap-southeast-2"  # Bedrock available region
    bedrock_agent_core_region: str = "us-west-2"
    
    # Strands
    strands_api_key: Optional[str] = None
    
    # Database
    database_url: str = "sqlite:///./government_services.db"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 30
    
    # Malaysian Government Services
    jpj_base_url: str = "https://mysikap.jpj.gov.my"
    lhdn_base_url: str = "https://www.hasil.gov.my"
    jpn_base_url: str = "https://www.jpn.gov.my"
    epf_base_url: str = "https://www.kwsp.gov.my"
    
    # External APIs
    tavily_api_key: Optional[str] = None
    crawl4ai_api_key: Optional[str] = None
    nova_act_api_key: Optional[str] = os.getenv("NOVA_ACT_API_KEY")
    
    # LLM API Keys for Crawl4AI
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"


# Global settings instance
settings = Settings()
