import os
from typing import Dict, Any

def save_env_report_to_file(report_markdown: str, filename: str) -> Dict[str, Any]:
	print(f"[TOOL] save_env_report_to_file called with filename={filename}")

	folder = os.path.dirname(filename)
	if folder and not os.path.exists(folder):
		os.makedirs(folder, exist_ok=True)

	full_path = os.path.abspath(filename)
	with open(full_path, "w", encoding="utf-8") as f:
		f.write(report_markdown)

	print(f"[TOOL] Report saved to {full_path}")
	return {"status": "success", "path": full_path}

