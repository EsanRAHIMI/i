"""
Agentic Core module for Ai Department.

This module contains the central AI reasoning, planning, and task execution engine.
"""

try:
    from .agentic_core import AgenticCore
    from .intent_recognizer import IntentRecognizer
    from .task_planner import TaskPlanner
    from .action_executor import ActionExecutor
    from .context_manager import ContextManager
except Exception:  # pragma: no cover
    AgenticCore = None
    IntentRecognizer = None
    TaskPlanner = None
    ActionExecutor = None
    ContextManager = None

__all__ = [
    "AgenticCore",
    "IntentRecognizer", 
    "TaskPlanner",
    "ActionExecutor",
    "ContextManager"
]