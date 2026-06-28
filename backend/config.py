"""
DevLens AI - Configuration
"""
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    APP_NAME: str = "DevLens AI"
    APP_VERSION: str = "1.0.0"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    GITHUB_TOKEN: str = ""
    GITHUB_API_BASE: str = "https://api.github.com"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    DATABASE_URL: str = "sqlite:///./data/devlens.db"
    CHROMA_PERSIST_DIR: str = "./data/chroma"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
