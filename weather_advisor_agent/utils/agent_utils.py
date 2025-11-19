from google.adk.agents.callback_context import CallbackContext
from google.genai.types import Content

def suppress_output_callback(callback_context: CallbackContext) -> Content:
  return Content()