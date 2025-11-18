import os
from dataclasses import dataclass
from dotenv import load_dotenv
import google.auth

def _configure_env() -> None:
    load_dotenv()
    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", None)
    if use_vertex is not None and use_vertex.upper() == "FALSE":
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
        return

    try:
        credentials, project_id = google.auth.default()
    except Exception:
        return

    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

_configure_env()

@dataclass
class EnviroConfiguration:
    """Configuration for environmental agent models and parameters."""
    critic_model: str = "gemini-2.5-flash-lite"
    worker_model: str = "gemini-2.5-flash-lite"
    max_iterations: int = 3

config = EnviroConfiguration()
