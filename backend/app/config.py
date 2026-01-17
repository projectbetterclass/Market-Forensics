"""Application configuration."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # HTTP client
    http_timeout: int = 30
    
    # Data sources
    yahoo_finance_base_url: str = "https://query1.finance.yahoo.com"
    edgar_base_url: str = "https://data.sec.gov"
    gdelt_base_url: str = "https://api.gdeltproject.org/api/v2"
    fred_base_url: str = "https://api.stlouisfed.org/fred"
    
    # Alpha Vantage API key (for symbol universe)
    alphavantage_api_key: str = "demo"
    
    # OpenAI settings (for LLM-guardrailed rendering)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 4000
    openai_temperature: float = 0.3
    
    # Scoring weights
    timing_weight: float = 0.30
    authority_weight: float = 0.25
    specificity_weight: float = 0.20
    magnitude_weight: float = 0.15
    corroboration_weight: float = 0.10
    
    # Cache settings
    chart_cache_refresh_seconds: int = 60
    context_cache_refresh_seconds: int = 300
    valuation_cache_refresh_seconds: int = 3600
    pattern_cache_refresh_seconds: int = 600
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
