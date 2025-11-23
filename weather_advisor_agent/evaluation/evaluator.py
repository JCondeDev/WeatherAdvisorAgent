from typing import Dict, Any, List
from dataclasses import dataclass
import logging
import datetime

logger = logging.getLogger(__name__)

@dataclass
class EvaluationResult:
    """Result of an agent evaluation"""
    category: str
    score: float
    details: str
    passed: bool

class TheophrastusEvaluator:
    """Evaluates the quality of agent outputs."""
    def __init__(self):
      self.evaluation_history: List[Dict[str, Any]] = []
    
    def evaluate_data_completeness(self, env_snapshot: Any) -> EvaluationResult:
      if not env_snapshot:
        return EvaluationResult(
          category="data_completeness",
          score=0.0,
          details="No environmental snapshot found",
          passed=False
        )
      
      required_fields = ["temperature_c", "wind_speed_10m_ms", "relative_humidity_percent"]
      
      if isinstance(env_snapshot, dict):
        current = env_snapshot.get("current", {})
        present_fields = sum(1 for f in required_fields if f in current and current[f] is not None)
        score = present_fields / len(required_fields)
        
        return EvaluationResult(
          category="data_completeness",
          score=score,
          details=f"{present_fields}/{len(required_fields)} required fields present",
          passed=score >= 0.8
        )
      
      return EvaluationResult(
        category="data_completeness",
        score=0.5,
        details="Unexpected snapshot format",
        passed=False
      )
    
    def evaluate_risk_assessment(self, env_risk_report: Dict[str, Any]) -> EvaluationResult:
        """Evaluate risk assessment quality"""
        if not env_risk_report:
          return EvaluationResult(
            category="risk_assessment",
            score=0.0,
            details="No risk report generated",
            passed=False
          )
        
        required_risks = ["heat_risk", "cold_risk", "wind_risk", "overall_risk"]
        valid_levels = {"low", "moderate", "medium", "high", "unknown"}
        
        present_risks = sum(1 for r in required_risks if r in env_risk_report)
        valid_values = sum(1 for r in required_risks if r in env_risk_report and env_risk_report[r] in valid_levels)
        score = (present_risks / len(required_risks)) * (valid_values / max(present_risks, 1))
        
        return EvaluationResult(
          category="risk_assessment",
          score=score,
          details=f"{present_risks}/{len(required_risks)} risk categories, {valid_values} valid",
          passed=score >= 0.75
        )
    
    def evaluate_recommendation_quality(self, advice_markdown: str) -> EvaluationResult:
      if not advice_markdown or len(advice_markdown) < 100:
        return EvaluationResult(
          category="recommendation_quality",
          score=0.0,
          details="Missing or too short recommendations",
          passed=False
        )
      
      required_sections = [
        "# Theophrastus Weather & Activity Report",
        "## 1. Summary",
        "## 2. Conditions",
        "## 3. Recommendations"
      ]
      
      present_sections = sum(1 for section in required_sections if section in advice_markdown)
      score = present_sections / len(required_sections)
      
      return EvaluationResult(
        category="recommendation_quality",
        score=score,
        details=f"{present_sections}/{len(required_sections)} required sections present",
        passed=score >= 0.75
      )
    
    def run_full_evaluation(self,env_snapshot: Any,env_risk_report: Dict[str, Any],advice_markdown: str) -> Dict[str, Any]:
      results = [
        self.evaluate_data_completeness(env_snapshot),
        self.evaluate_risk_assessment(env_risk_report),
        self.evaluate_recommendation_quality(advice_markdown)
      ]
      
      overall_score = sum(r.score for r in results) / len(results)
      all_passed = all(r.passed for r in results)
      
      evaluation = {
        "timestamp": str(datetime.now()),
        "overall_score": overall_score,
        "passed": all_passed,
        "results": [
          {
            "category": r.category,
            "score": r.score,
            "details": r.details,
            "passed": r.passed
          }
          for r in results
        ]
      }
      
      self.evaluation_history.append(evaluation)
      logger.info(f"Evaluation complete: Score={overall_score:.2f}, Passed={all_passed}")
      
      return evaluation
