import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env file from project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")


class Config:
    # API Keys
    SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY")
    CHUTES_API_KEY = os.getenv("CHUTES_API_KEY")
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
