"""
Developed a built-in local evaluator for testing, diagnostics and watch behaviour of agents and tools when the UI Eval integration
was having executing errors.
Useful to see how efective is the agent is working and if something is missing without the integrated UI.
Helped me to localize loss of agent keys requiered for each response.
Still working in the functionality for 1,2 output keys cases.
"""
import json
import logging
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class EvaluationResult:
  """Result of an agent evaluation"""
  category: str
  score: float
  details: str
  passed: bool
  timestamp: str = None
  
  def __post_init__(self):
    if self.timestamp is None:
      self.timestamp = datetime.datetime.now().isoformat()

@dataclass
class FullEvaluationReport:
  """Complete evaluation report for a Theophrastus run"""
  session_id: str
  timestamp: str
  overall_score: float
  passed: bool
  evaluations: List[EvaluationResult]
  summary: str
  
  def to_dict(self) -> Dict[str, Any]:
    return {
      "session_id": self.session_id,
      "timestamp": self.timestamp,
      "overall_score": self.overall_score,
      "passed": self.passed,
      "evaluations": [asdict(e) for e in self.evaluations],
      "summary": self.summary
    }

class TheophrastusEvaluator:
  """Evaluates the quality of Theophrastus agent outputs."""
  
  def __init__(self, output_dir: Optional[Path] = None):
    self.evaluation_history: List[FullEvaluationReport] = []
    self.output_dir = output_dir or Path("weather_advisor_agent/data/evaluations")
    self.output_dir.mkdir(parents=True, exist_ok=True)
  
  def evaluate_data_completeness(self, env_snapshot: Any) -> EvaluationResult:
    """Evaluate if environmental data snapshot has required fields"""
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
    
    elif isinstance(env_snapshot, list):
        if not env_snapshot:

          return EvaluationResult(
            category="data_completeness",
            score=0.0,
            details="Empty snapshot list",
            passed=False
          )
        
        total_score = 0.0
        for snapshot in env_snapshot:
          if isinstance(snapshot, dict):
            current = snapshot.get("current", {})
            present_fields = sum(1 for f in required_fields if f in current and current[f] is not None)
            total_score += present_fields / len(required_fields)
        
        avg_score = total_score / len(env_snapshot)

        return EvaluationResult(
          category="data_completeness",
          score=avg_score,
          details=f"Average completeness across {len(env_snapshot)} locations: {avg_score:.2%}",
          passed=avg_score >= 0.8
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
    
    if isinstance(env_risk_report, str):
      try:
        env_risk_report = json.loads(env_risk_report)
      except json.JSONDecodeError:
        return EvaluationResult(
          category="risk_assessment",
          score=0.0,
          details="Invalid JSON risk report",
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
      details=f"{present_risks}/{len(required_risks)} risk categories, {valid_values} valid levels",
      passed=score >= 0.75
    )
  
  def evaluate_recommendation_quality(self, advice_markdown: str) -> EvaluationResult:
    """Evaluate the quality of Aurora's recommendations"""
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
    structure_score = present_sections / len(required_sections)
    
    word_count = len(advice_markdown.split())
    length_score = min(1.0, word_count / 200)
    
    score = (structure_score * 0.6) + (length_score * 0.4)
    
    return EvaluationResult(
      category="recommendation_quality",
      score=score,
      details=f"{present_sections}/{len(required_sections)} sections, {word_count} words",
      passed=score >= 0.7
    )
  
  def evaluate_location_search(self, env_location_options: List[Dict[str, Any]]) -> EvaluationResult:
    """Evaluate quality of location search results"""
    if not env_location_options:
      return EvaluationResult(
        category="location_search",
        score=0.0,
        details="No location options found",
        passed=False
      )
    
    if not isinstance(env_location_options, list):
      return EvaluationResult(
        category="location_search",
        score=0.0,
        details="Invalid location options format",
        passed=False
      )
    
    valid_locations = 0
    for loc in env_location_options:
      if isinstance(loc, dict):
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        name = loc.get("name")
        
        if lat is not None and lon is not None and name:
          try:
            lat_f = float(lat)
            lon_f = float(lon)
            if -90 <= lat_f <= 90 and -180 <= lon_f <= 180:
              valid_locations += 1
          except (TypeError, ValueError):
            pass
    
    score = valid_locations / len(env_location_options)
    
    return EvaluationResult(
      category="location_search",
      score=score,
      details=f"{valid_locations}/{len(env_location_options)} valid locations",
      passed=score >= 0.8
    )

  def evaluate_workflow_completeness(self, session_state: Dict[str, Any], complexity: str = "medium") -> EvaluationResult:
    """
    Evaluate if the workflow completed successfully based on query complexity.
    
    Different query types require different workflows:
    - "simple" weather query: Only needs env_snapshot
    - "medium" location search: Only needs env_location_options  
    - "medium" weather for locations: Needs env_snapshot + env_risk_report + env_advice_markdown
    - "complex" full report: Needs all workflow steps
    
    Args:
        session_state: Current session state
        complexity: Query complexity level
    
    Returns:
        EvaluationResult with workflow completeness assessment
    """
    def is_valid_value(value: Any) -> bool:
      """Check if a value is actually valid, not just truthy"""
      if value is None:
        return False
      if isinstance(value, dict):
        return len(value) > 0
      if isinstance(value, list):
        return len(value) > 0
      if isinstance(value, str):
        return len(value.strip()) > 0
      return bool(value)
    
    # Check what workflow components are present
    has_snapshot = "env_snapshot" in session_state and is_valid_value(session_state["env_snapshot"])
    has_locations = "env_location_options" in session_state and is_valid_value(session_state["env_location_options"])
    has_risk = "env_risk_report" in session_state and is_valid_value(session_state["env_risk_report"])
    has_advice = "env_advice_markdown" in session_state and is_valid_value(session_state["env_advice_markdown"])
    
    # SIMPLE queries - just weather data
    if complexity == "simple":
        if has_snapshot:
            return EvaluationResult(
                category="workflow_completeness",
                score=1.0,
                details="Simple weather query completed successfully",
                passed=True
            )
        else:
            return EvaluationResult(
                category="workflow_completeness",
                score=0.0,
                details="Missing env_snapshot for weather query",
                passed=False
            )
    
    # MEDIUM queries - either location search OR weather with advice
    elif complexity == "medium":
        # Case 1: Pure location search (has locations, no weather data yet)
        if has_locations and not has_snapshot:
            return EvaluationResult(
                category="workflow_completeness",
                score=1.0,
                details="Location search completed successfully",
                passed=True
            )
        
        # Case 2: Weather data for locations (should have snapshot + risk + advice)
        elif has_snapshot:
            required = ["env_snapshot", "env_risk_report", "env_advice_markdown"]
            present = [k for k in required if k in session_state and is_valid_value(session_state[k])]
            score = len(present) / len(required)
            
            if score >= 1.0:
                return EvaluationResult(
                    category="workflow_completeness",
                    score=1.0,
                    details=f"Complete workflow: {len(present)}/{len(required)} steps",
                    passed=True
                )
            else:
                missing = [k for k in required if k not in session_state or not is_valid_value(session_state[k])]
                return EvaluationResult(
                    category="workflow_completeness",
                    score=score,
                    details=f"Workflow steps completed: {len(present)}/{len(required)} (missing: {', '.join(missing)})",
                    passed=False
                )
        
        # Case 3: Neither locations nor snapshot (incomplete)
        else:
            return EvaluationResult(
                category="workflow_completeness",
                score=0.0,
                details="No workflow components found (expected location search or weather data)",
                passed=False
            )
    
    # COMPLEX queries - full report with all components
    else:  # complexity == "complex"
        required = ["env_snapshot", "env_risk_report", "env_advice_markdown"]
        present = [k for k in required if k in session_state and is_valid_value(session_state[k])]
        score = len(present) / len(required)
        
        if score >= 1.0:
            return EvaluationResult(
                category="workflow_completeness",
                score=1.0,
                details=f"Complete workflow: {len(present)}/{len(required)} steps",
                passed=True
            )
        else:
            missing = [k for k in required if k not in session_state or not is_valid_value(session_state[k])]
            return EvaluationResult(
                category="workflow_completeness",
                score=score,
                details=f"Workflow steps completed: {len(present)}/{len(required)} (missing: {', '.join(missing)})",
                passed=False
            )
  
  def evaluate_response_time(self, duration_seconds: float, complexity: str = "simple") -> EvaluationResult:
    """Evaluate response time performance"""
    thresholds = {
      "simple": 30,    # Simple weather query
      "medium": 60,    # Location search + weather
      "complex": 120   # Full report generation
    }
    
    threshold = thresholds.get(complexity, 60)
    
    if duration_seconds <= threshold:
      score = 1.0
      details = f"Response time {duration_seconds:.1f}s (threshold: {threshold}s) - Excellent"
    elif duration_seconds <= threshold * 1.5:
      score = 0.7
      details = f"Response time {duration_seconds:.1f}s (threshold: {threshold}s) - Acceptable"
    else:
      score = 0.3
      details = f"Response time {duration_seconds:.1f}s (threshold: {threshold}s) - Slow"
    
    return EvaluationResult(
      category="response_time",
      score=score,
      details=details,
      passed=duration_seconds <= threshold * 1.5
    )
  
  def run_full_evaluation(
      self,
      session_id: str,
      session_state: Dict[str, Any],
      duration_seconds: Optional[float] = None,
      complexity: str = "medium"
  ) -> FullEvaluationReport:
      """Run complete evaluation on a Theophrastus session"""
      
      # Check for _evaluation_snapshot first (where callback stores data)
      evaluation_data = session_state.get("_evaluation_snapshot", {})
      
      # If no _evaluation_snapshot, use session_state directly as fallback
      if not evaluation_data:
          evaluation_data = session_state
      
      evaluations = []
      
      # Use evaluation_data instead of session_state for all checks
      # 1. Data completeness
      if "env_snapshot" in evaluation_data:
          snapshot = evaluation_data["env_snapshot"]
          # Parse if string
          if isinstance(snapshot, str):
              try:
                  snapshot = json.loads(snapshot)
              except:
                  pass
          evaluations.append(
              self.evaluate_data_completeness(snapshot)
          )
      
      # 2. Location search (if applicable)
      if "env_location_options" in evaluation_data:
          evaluations.append(
              self.evaluate_location_search(evaluation_data["env_location_options"])
          )
      
      # 3. Risk assessment
      if "env_risk_report" in evaluation_data:
          evaluations.append(
              self.evaluate_risk_assessment(evaluation_data["env_risk_report"])
          )
      
      # 4. Recommendation quality
      if "env_advice_markdown" in evaluation_data:
          evaluations.append(
              self.evaluate_recommendation_quality(evaluation_data["env_advice_markdown"])
          )
      
      # 5. Workflow completeness - PASS COMPLEXITY HERE!
      evaluations.append(
          self.evaluate_workflow_completeness(evaluation_data, complexity)
      )
      
      # 6. Response time (if provided)
      if duration_seconds is not None:
          evaluations.append(
              self.evaluate_response_time(duration_seconds, complexity)
          )
      
      # Calculate overall score
      overall_score = sum(e.score for e in evaluations) / len(evaluations) if evaluations else 0.0
      passed = all(e.passed for e in evaluations)
      
      # Generate summary
      passed_count = sum(1 for e in evaluations if e.passed)
      summary = f"{passed_count}/{len(evaluations)} evaluations passed. Overall score: {overall_score:.2%}"
      
      report = FullEvaluationReport(
          session_id=session_id,
          timestamp=datetime.datetime.now().isoformat(),
          overall_score=overall_score,
          passed=passed,
          evaluations=evaluations,
          summary=summary
      )
      
      self.evaluation_history.append(report)
      
      logger.info(f"Evaluation complete: {summary}")
      for eval_result in evaluations:
          status = "PASSED" if eval_result.passed else "FAILED"
          logger.info(f"  {status} - {eval_result.category}: {eval_result.score:.2%} - {eval_result.details}")
      
      return report
    
  def save_evaluation(self, report: FullEvaluationReport) -> Path:
    """Save evaluation report to file"""
    filename = f"evaluation_{report.session_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = self.output_dir / filename
    
    with open(filepath, 'w') as f:
      json.dump(report.to_dict(), f, indent=2)
    
    logger.info(f"Evaluation saved to {filepath}")
    return filepath
  
  def print_evaluation_report(self, report: FullEvaluationReport):
    """Evaluation report"""
    print("\n" + "="*80)
    print(f"THEOPHRASTUS EVALUATION REPORT")
    print("="*80)
    print(f"Session: {report.session_id}")
    print(f"Timestamp: {report.timestamp}")
    print(f"Overall Score: {report.overall_score:.1%}")
    print(f"Status: {'PASSED' if report.passed else 'FAILED'}")
    print(f"\nSummary: {report.summary}")
    print("\n" + "="*80)
    print("DETAILED RESULTS:")
    print("="*80)
    
    for eval_result in report.evaluations:
      status = "PASS" if eval_result.passed else "FAIL"
      print(f"\n{eval_result.category.replace('_', ' ').title()}")
      print(f"  Status: {status}")
      print(f"  Score: {eval_result.score:.1%}")
      print(f"  Details: {eval_result.details}")
    
    print("\n" + "="*80 + "\n")
  
  def get_evaluation_statistics(self) -> Dict[str, Any]:
    """Get statistics from all evaluations"""
    if not self.evaluation_history:
      return {"total_evaluations": 0}
    
    total = len(self.evaluation_history)
    passed = sum(1 for r in self.evaluation_history if r.passed)
    avg_score = sum(r.overall_score for r in self.evaluation_history) / total
    
    category_stats = {}
    for report in self.evaluation_history:
      for eval_result in report.evaluations:
        cat = eval_result.category
        if cat not in category_stats:
          category_stats[cat] = {"scores": [], "passed": 0}
        category_stats[cat]["scores"].append(eval_result.score)
        if eval_result.passed:
          category_stats[cat]["passed"] += 1
    
    for cat in category_stats:
      scores = category_stats[cat]["scores"]
      category_stats[cat]["avg_score"] = sum(scores) / len(scores)
      category_stats[cat]["pass_rate"] = category_stats[cat]["passed"] / len(scores)
    
    return {
      "total_evaluations": total,
      "passed": passed,
      "pass_rate": passed / total,
      "average_score": avg_score,
      "category_statistics": category_stats
    }