import datetime
from pathlib import Path

def save_env_report_to_file(report_markdown: str, filename: str) -> str:
  """Saves report to .md format"""
  base_dir = Path("reports")
  file = f"{filename}_recommendations_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
  full_path = base_dir / file
  full_path.parent.mkdir(parents=True, exist_ok=True)

  with open(full_path, "w", encoding="utf-8") as f:
    f.write(report_markdown)

  return f"Report saved to: {full_path}"