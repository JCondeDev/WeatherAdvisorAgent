import os
import logging

from google.genai import types
from dataclasses import dataclass, field
from dotenv import load_dotenv

def _configure_env() -> None:
  load_dotenv()
  os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"

_configure_env()

logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@dataclass
class TheophrastusConfiguration:
  root_model: str = "gemini-2.5-flash"
  worker_model: str = "gemini-2.5-flash"
  critic_model: str = "gemini-2.5-pro"
  mapper_model: str = "gemini-2.0-flash-lite"
  writer_model: str = "gemini-2.0-flash-lite"
  max_iterations: int = 2
  
  model_params: dict = field(default_factory=lambda: {
    "temperature": 0.2,
    "max_output_tokens": 2048
  })

  retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504]
  )

  default_location_name: str = "Ciudad de México, México"
  
  enable_tracing: bool = True
  log_level: str = "INFO"