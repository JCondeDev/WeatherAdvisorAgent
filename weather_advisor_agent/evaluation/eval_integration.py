"""
Evaluation Integration for Theophrastus Root Agent

This module provides utilities to integrate evaluation directly into the agent workflow.
"""

from typing import Optional, Dict, Any
import logging
from google.adk.agents.callback_context import CallbackContext
from google.genai.types import Content, Part

from weather_advisor_agent.evaluation.evaluator import TheophrastusEvaluator, FullEvaluationReport

logger = logging.getLogger(__name__)

class EvaluationCallbackHandler:
    """Handles evaluation callbacks during agent execution"""
    
    def __init__(self, evaluator: Optional[TheophrastusEvaluator] = None):
        self.evaluator = evaluator or TheophrastusEvaluator()
        self.current_report: Optional[FullEvaluationReport] = None
    
    def create_evaluation_callback(self):
        """Create a callback function for agent evaluation"""
        
        def evaluation_callback(callback_context: CallbackContext) -> Content:
            """
            Callback that runs evaluation after agent completion.
            This can be used as an after_agent_callback in your root agent.
            """
            session = callback_context.session
            session_state = session.state
            
            # Run evaluation
            try:
                evaluation_report = self.evaluator.run_full_evaluation(
                    session_id=session.id,
                    session_state=session_state,
                    complexity="medium"  # Default complexity
                )
                
                # Store report
                self.current_report = evaluation_report
                
                # Optionally save to file
                self.evaluator.save_evaluation(evaluation_report)
                
                # Store evaluation in session state for reference
                session_state["_evaluation_report"] = evaluation_report.to_dict()
                
                # Log summary
                logger.info(f"Evaluation complete: {evaluation_report.summary}")
                
                # Return success message
                if evaluation_report.passed:
                    return Content(parts=[Part(text="✓ All quality checks passed")])
                else:
                    failed = [e.category for e in evaluation_report.evaluations if not e.passed]
                    return Content(parts=[Part(text=f"⚠️ Quality checks failed: {', '.join(failed)}")])
                
            except Exception as e:
                logger.error(f"Evaluation failed: {e}", exc_info=True)
                return Content(parts=[Part(text="Evaluation error occurred")])
        
        return evaluation_callback
    
    def get_latest_report(self) -> Optional[FullEvaluationReport]:
        """Get the most recent evaluation report"""
        return self.current_report


class InlineEvaluator:
    """
    Inline evaluator for immediate validation during workflow.
    Can be used in validation checkers or between agent steps.
    """
    
    def __init__(self):
        self.evaluator = TheophrastusEvaluator()
    
    def validate_snapshot(self, session_state: Dict[str, Any]) -> bool:
        """Quick validation of environmental snapshot"""
        snapshot = session_state.get("env_snapshot")
        if not snapshot:
            logger.warning("Inline eval: No snapshot found")
            return False
        
        result = self.evaluator.evaluate_data_completeness(snapshot)
        
        if not result.passed:
            logger.warning(f"Inline eval: Snapshot validation failed - {result.details}")
        
        return result.passed
    
    def validate_risk_report(self, session_state: Dict[str, Any]) -> bool:
        """Quick validation of risk report"""
        risk_report = session_state.get("env_risk_report")
        if not risk_report:
            logger.warning("Inline eval: No risk report found")
            return False
        
        result = self.evaluator.evaluate_risk_assessment(risk_report)
        
        if not result.passed:
            logger.warning(f"Inline eval: Risk report validation failed - {result.details}")
        
        return result.passed
    
    def validate_advice(self, session_state: Dict[str, Any]) -> bool:
        """Quick validation of advice markdown"""
        advice = session_state.get("env_advice_markdown")
        if not advice:
            logger.warning("Inline eval: No advice markdown found")
            return False
        
        result = self.evaluator.evaluate_recommendation_quality(advice)
        
        if not result.passed:
            logger.warning(f"Inline eval: Advice validation failed - {result.details}")
        
        return result.passed
    
    def validate_full_workflow(self, session_state: Dict[str, Any]) -> Dict[str, bool]:
        """Validate all workflow components, return status dict"""
        return {
            "snapshot": self.validate_snapshot(session_state),
            "risk_report": self.validate_risk_report(session_state),
            "advice": self.validate_advice(session_state),
        }


def create_evaluation_validator_agent():
    """
    Example: Create a validation agent that uses evaluation metrics.
    
    This can be added to your agent workflow to check quality mid-execution.
    """
    from google.adk.agents import Agent
    
    inline_eval = InlineEvaluator()
    
    evaluation_agent = Agent(
        name="quality_validator",
        model="gemini-2.0-flash-lite",
        description="Validates output quality using evaluation metrics",
        instruction="""
        You are a quality validation agent. Check the session state and validate:
        1. Environmental snapshot completeness
        2. Risk report quality
        3. Recommendation quality
        
        Report any quality issues found.
        """,
        after_agent_callback=lambda ctx: _evaluation_validator_callback(ctx, inline_eval),
        output_key="quality_validation_result"
    )
    
    return evaluation_agent


def _evaluation_validator_callback(callback_context: CallbackContext, inline_eval: InlineEvaluator) -> Content:
    """Internal callback for validation agent"""
    state = callback_context.session.state
    
    validation_results = inline_eval.validate_full_workflow(state)
    
    all_passed = all(validation_results.values())
    failed_components = [k for k, v in validation_results.items() if not v]
    
    if all_passed:
        message = "✓ All quality validations passed"
        logger.info(message)
    else:
        message = f"⚠️ Quality issues in: {', '.join(failed_components)}"
        logger.warning(message)
    
    state["_quality_validation"] = {
        "passed": all_passed,
        "results": validation_results,
        "failed_components": failed_components
    }
    
    return Content(parts=[Part(text=message)])