"""
Developed a built-in local observavility and log module
for testing, diagnostics and watch behaviour if agents and tools.
Useful for debbuging strange behaviours of agents when running tests without UI.
"""
import logging
import time
import json
from datetime import datetime
from pathlib import Path

from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from dataclasses import dataclass, field

logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
  datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

@dataclass
class TraceSpan:
  name: str
  start_time: float
  end_time: Optional[float] = None
  parent_span_id: Optional[str] = None
  span_id: str = ""
  attributes: Dict[str, Any] = field(default_factory=dict)
  status: str = "in_progress"
  
  def __post_init__(self):
    if not self.span_id:
      self.span_id = f"{self.name}_{int(self.start_time * 1000)}"
  
  @property
  def duration_ms(self) -> Optional[float]:
    if self.end_time:
      return (self.end_time - self.start_time) * 1000
    return None
  
  def to_dict(self) -> Dict[str, Any]:
    """Convert span to dictionary for logging/storage"""
    return {
      "span_id": self.span_id,
      "name": self.name,
      "start_time": self.start_time,
      "end_time": self.end_time,
      "duration_ms": self.duration_ms,
      "status": self.status,
      "attributes": self.attributes,
      "parent_span_id": self.parent_span_id
      }


class TheophrastusMetrics:
  def __init__(self):
    self.start_time = datetime.now()
    
    self.agent_invocations = 0
    self.tool_calls = 0
    self.successful_operations = 0
    self.failed_operations = 0
    self.validation_checks = 0
    self.validation_failures = 0
    self.agent_call_counts: Dict[str, int] = {}
    self.tool_call_counts: Dict[str, int] = {}
    self.error_counts: Dict[str, int] = {}
    self.agent_durations: Dict[str, List[float]] = {}
    self.tool_durations: Dict[str, List[float]] = {}
    
  def increment_agent_calls(self, agent_name: str):
    self.agent_invocations += 1
    self.agent_call_counts[agent_name] = self.agent_call_counts.get(agent_name, 0) + 1

  def increment_tool_calls(self, tool_name: str):
    self.tool_calls += 1
    self.tool_call_counts[tool_name] = self.tool_call_counts.get(tool_name, 0) + 1
  
  def record_agent_duration(self, agent_name: str, duration_ms: float):
    if agent_name not in self.agent_durations:
      self.agent_durations[agent_name] = []
    self.agent_durations[agent_name].append(duration_ms)
  
  def record_tool_duration(self, tool_name: str, duration_ms: float):
    if tool_name not in self.tool_durations:
      self.tool_durations[tool_name] = []
    self.tool_durations[tool_name].append(duration_ms)
  
  def record_error(self, error_type: str):
    self.failed_operations += 1
    self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
  
  def get_summary(self) -> Dict[str, Any]:
    runtime = (datetime.now() - self.start_time).total_seconds()

    avg_agent_durations = {name: sum(durations) / len(durations) for name, durations in self.agent_durations.items()if durations}
    avg_tool_durations = {name: sum(durations) / len(durations) for name, durations in self.tool_durations.items()if durations}
    total_operations = self.successful_operations + self.failed_operations
    
    success_rate = ((self.successful_operations / total_operations * 100) if total_operations > 0 else 0)
    
    return {
        "runtime_seconds": round(runtime, 2),
        "total_agent_invocations": self.agent_invocations,
        "total_tool_calls": self.tool_calls,
        "successful_operations": self.successful_operations,
        "failed_operations": self.failed_operations,
        "success_rate_percent": round(success_rate, 2),
        "validation_checks": self.validation_checks,
        "validation_failures": self.validation_failures,
        "agent_call_breakdown": self.agent_call_counts,
        "tool_call_breakdown": self.tool_call_counts,
        "error_breakdown": self.error_counts,
        "avg_agent_durations_ms": avg_agent_durations,
        "avg_tool_durations_ms": avg_tool_durations
    }
  
  def print_summary(self):
    summary = self.get_summary()
    
    print("METRICS SUMMARY")
    print(f" -Runtime: {summary['runtime_seconds']}s")
    print(f" -Agent Invocations: {summary['total_agent_invocations']}")
    print(f" -Tool Calls: {summary['total_tool_calls']}")
    print(f" -Success Rate: {summary['success_rate_percent']}%")
    print(f" -Failed Operations: {summary['failed_operations']}")
    
    print("\n" + "="*80)
    if summary['agent_call_breakdown']:
      print("\n -Agent Calls:")
      for agent, count in sorted(summary['agent_call_breakdown'].items()):
        print(f"  *{agent}: {count}")
  
    if summary['tool_call_breakdown']:
      print("\n -Tool Calls:")
      for tool, count in sorted(summary['tool_call_breakdown'].items()):
        print(f"  *{tool}: {count}")
    
    if summary['error_breakdown']:
      print("\n -Errors:")
      for error, count in sorted(summary['error_breakdown'].items()):
        print(f"  *{error}: {count}")

class TheophrastusObservability:   
    def __init__(self, enable_traces: bool = True):
      self.logger = logging.getLogger("Theophrastus")
      self.metrics = TheophrastusMetrics()
      self.enable_traces = enable_traces
      self.traces: List[TraceSpan] = []
      self.active_spans: Dict[str, TraceSpan] = {}
    
    def log_agent_start(self, agent_name: str, context: Optional[Dict[str, Any]] = None):
      self.metrics.increment_agent_calls(agent_name)
      context_str = f"Context: {context}" if context else ""
      self.logger.info(f"[--AGENT--] {agent_name} {context_str} |\n")
    
    def log_agent_complete(self,agent_name: str,output_key: str,success: bool = True,duration_ms: Optional[float] = None):
      if success:
        self.metrics.successful_operations += 1
        status = "SUCCESS"
      else:
        self.metrics.failed_operations += 1
        status = "FAILED"
      
      self.logger.info(f"[--AGENT--] {agent_name} | Output: {output_key} | {status} |\n")
      
      if duration_ms:
        self.metrics.record_agent_duration(agent_name, duration_ms)
    
    def log_tool_call(self, tool_name: str, params: Dict[str, Any]):
      self.metrics.increment_tool_calls(tool_name)
      param_preview = str(params)[:100]
      self.logger.info(f"[--TOOL--] {tool_name} | Params: {param_preview} |\n")
    
    def log_tool_complete(self,tool_name: str,success: bool = True,duration_ms: Optional[float] = None):
      if success:
        status = "SUCCESS"
      else:
        status = "FAILED"

      self.logger.info(f"[--TOOL--] {tool_name} | {status} |\n")
      
      if duration_ms:
        self.metrics.record_tool_duration(tool_name, duration_ms)
    
    def log_validation(self, checker_name: str, passed: bool, details: str = ""):
      self.metrics.validation_checks += 1
      if not passed:
        self.metrics.validation_failures += 1
      
      if passed:
        status = "PASSED"
      else:
        status = "NOT PASSED"

      self.logger.info(f"[--VALIDATION--] {checker_name} | {status} |\n")
  
    def log_error(self, context: str, error: Exception, details: Optional[str] = None):
      error_type = type(error).__name__
      self.metrics.record_error(error_type)
      self.logger.error(f"[--ERROR--] {context} | {error_type}: {str(error)} |\n",exc_info=True)
    
    def log_state_change(self, key: str, action: str, value_preview: str = ""):
      preview = f"Value: {value_preview[:50]}" if value_preview else ""
      self.logger.debug(f"[--STATE--] {action} key '{key}' {preview} |\n")
    

    @contextmanager
    def trace_operation(self,operation_name: str,attributes: Optional[Dict[str, Any]] = None,parent_span_id: Optional[str] = None):
      if not self.enable_traces:
        yield None
        return
      
      span = TraceSpan(name=operation_name,start_time=time.time(),parent_span_id=parent_span_id,attributes=attributes or {})
      self.active_spans[span.span_id] = span
      self.logger.debug(f"[--TRACE--] {operation_name} | span_id: {span.span_id} |\n")
      
      try:
        yield span
        span.status = "success"
        span.end_time = time.time()
        self.logger.debug(f"[--TRACE--] {operation_name} | Success |\n")
      except Exception as e:
        span.status = "error"
        span.end_time = time.time()
        span.attributes["error"] = str(e)
        span.attributes["error_type"] = type(e).__name__
        self.logger.debug(f"[--TRACE--] {operation_name} | Error | Type: {type(e).__name__} |\n")
        raise
      finally:
        self.traces.append(span)
        if span.span_id in self.active_spans:
          del self.active_spans[span.span_id]
    
    def get_trace_summary(self) -> Dict[str, Any]:
      if not self.traces:
        return {"message": "No traces recorded"}
      
      total_traces = len(self.traces)
      successful_traces = sum(1 for t in self.traces if t.status == "success")
      failed_traces = sum(1 for t in self.traces if t.status == "error")

      durations = [t.duration_ms for t in self.traces if t.duration_ms is not None]
      avg_duration = sum(durations) / len(durations) if durations else 0
      max_duration = max(durations) if durations else 0
      min_duration = min(durations) if durations else 0
      
      return {
        "total_traces": total_traces,
        "successful": successful_traces,
        "failed": failed_traces,
        "avg_duration_ms": avg_duration,
        "max_duration_ms": max_duration,
        "min_duration_ms": min_duration,
        "traces": [t.to_dict() for t in self.traces[-10:]]
      }
    
    def export_traces(self, filename: str):
      """Export traces to JSON file"""
      trace_data = {"summary": self.get_trace_summary(),"all_traces": [t.to_dict() for t in self.traces]}
      
      base_dir = Path("weather_advisor_agent") / "data"
      file = f"{filename}_traces.json"
      full_path = base_dir / file
      full_path.parent.mkdir(parents=True, exist_ok=True)

      with open(full_path, 'w') as f:
        json.dump(trace_data, f, indent=2)

    def get_metrics_summary(self) -> Dict[str, Any]:
      """Get comprehensive metrics summary"""
      return self.metrics.get_summary()
    
    def print_metrics_summary(self):
      """Print formatted metrics summary"""
      self.metrics.print_summary()
    
    def export_metrics(self, filename: str):
      """Export metrics to JSON file"""
      base_dir = Path("weather_advisor_agent") / "data"
      file = f"{filename}_metrics.json"
      full_path = base_dir / file
      full_path.parent.mkdir(parents=True, exist_ok=True)

      with open(full_path, 'w') as f:
        json.dump(self.metrics.get_summary(), f, indent=2)
        

Theophrastus_Observability = TheophrastusObservability(enable_traces=True)

#Decorators
def trace_function(operation_name: Optional[str] = None):
  def decorator(func):
    def wrapper(*args, **kwargs):
      name = operation_name or func.__name__
      with Theophrastus_Observability.trace_operation(name):
        return func(*args, **kwargs)
    return wrapper
  return decorator

def log_exceptions(context: str):
  def decorator(func):
    def wrapper(*args, **kwargs):
      try:
        return func(*args, **kwargs)
      except Exception as e:
        Theophrastus_Observability.log_error(context, e, details=f"Function: {func.__name__} | \n")
        raise
    return wrapper
  return decorator