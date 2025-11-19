import os
from dataclasses import dataclass
from dotenv import load_dotenv

def _configure_env() -> None:
  load_dotenv()
  os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"

_configure_env()

@dataclass
class EnviroConfiguration:
  critic_model: str = "gemini-2.5-pro"
  worker_model: str = "gemini-2.5-flash"
  max_iterations: int = 2

  default_location_name: str = "Ciudad de México, México"

config = EnviroConfiguration()