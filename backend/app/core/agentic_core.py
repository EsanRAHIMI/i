"""
Agentic Core - Central AI reasoning, planning, and task execution engine.

This module orchestrates the entire AI assistant system, combining intent recognition,
task planning, action execution, and context management to provide intelligent
responses and autonomous task execution.
"""

import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio
import logging

from .intent_recognizer import IntentRecognizer, IntentResult, IntentType
from .task_planner import TaskPlanner, TaskPlan, TaskStatus
from .action_executor import ActionExecutor
from .context_manager import ContextManager, UserContext, ContextType

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Response from the agentic core."""
    
    text: str
    audio_url: Optional[str] = None
    actions: List[Dict[str, Any]] = None
    confidence_score: float = 0.0
    requires_confirmation: bool = False
    task_plan_id: Optional[str] = None
    context_updates: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.actions is None:
            self.actions = []
        if self.context_updates is None:
            self.context_updates = {}


@dataclass
class ExecutionResult:
    """Result of task plan execution."""
    
    success: bool
    task_plan: TaskPlan
    completed_steps: List[str]
    failed_steps: List[str]
    message: str
    execution_time_seconds: float


class AgenticCore:
    """
    Central AI reasoning, planning, and task execution engine.
    
    Orchestrates intent recognition, task planning, action execution,
    and context management to provide intelligent AI assistance.
    """
    
    def __init__(
        self,
        calendar_service=None,
        whatsapp_service=None,
        email_service=None,
        task_service=None,
        auth_service=None,
        redis_client=None
    ):
        # Initialize core components
        self.intent_recognizer = IntentRecognizer()
        self.task_planner = TaskPlanner()
        self.context_manager = ContextManager(redis_client=redis_client)
        
        # Initialize action executor with service dependencies
        self.action_executor = ActionExecutor(
            calendar_service=calendar_service,
            whatsapp_service=whatsapp_service,
            email_service=email_service,
            task_service=task_service,
            auth_service=auth_service
        )
        
        # Integrate action executor with task planner
        self._integrate_action_executor()
        
        # System state
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.system_paused = False
        
        logger.info("Agentic Core initialized")
    
    def _integrate_action_executor(self) -> None:
        """Integrate action executor with task planner."""
        
        # Override task planner's action executors with our concrete implementations
        executor_mapping = {
            "calendar_create_event": self.action_executor.execute_calendar_create_event,
            "calendar_update_event": self.action_executor.execute_calendar_update_event,
            "calendar_delete_event": self.action_executor.execute_calendar_delete_event,
            "calendar_query_events": self.action_executor.execute_calendar_query_events,
            "task_create": self.action_executor.execute_task_create,
            "task_update": self.action_executor.execute_task_update,
            "task_complete": self.action_executor.execute_task_complete,
            "message_send_whatsapp": self.action_executor.execute_whatsapp_send,
            "message_send_email": self.action_executor.execute_email_send,
            "message_schedule_reminder": self.action_executor.execute_schedule_reminder,
        }
        
        # Update task planner's action executors
        for action_type_str, executor_func in executor_mapping.items():
            # Convert string to ActionType enum
            try:
                from .task_planner import ActionType
                action_type = ActionType(action_type_str)
                self.task_planner.action_executors[action_type] = executor_func
            except ValueError:
                logger.warning(f"Unknown action type: {action_type_str}")
    
    async def process_user_input(
        self,
        text: str,
        user_id: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process user input and generate intelligent response.
        
        Args:
            text: User's natural language input
            user_id: Unique identifier for the user
            session_id: Optional session identifier
            context: Additional context information
            
        Returns:
            AgentResponse with text, actions, and context updates
        """
        
        if self.system_paused:
            return AgentResponse(
                text="I'm currently paused. Please say 'resume' to continue.",
                confidence_score=1.0
            )
        
        try:
            # Handle system control commands first
            if await self._handle_system_commands(text, user_id):
                return AgentResponse(
                    text="System command processed.",
                    confidence_score=1.0
                )
            
            # Get user context
            user_context = await self.context_manager.get_user_context(user_id)
            
            # Merge additional context
            if context:
                await self.context_manager.update_user_context(
                    user_id, context, ContextType.TEMPORAL
                )
            
            # Recognize intent
            intent_result = await self.intent_recognizer.recognize_intent(
                text, user_id, context
            )
            
            logger.info(f"Intent recognized: {intent_result.intent} (confidence: {intent_result.confidence})")
            
            # Generate response based on intent
            response = await self._generate_response(
                intent_result, user_id, user_context, text
            )
            
            # Update conversation history
            await self.context_manager.add_conversation_turn(
                user_id=user_id,
                user_input=text,
                ai_response=response.text,
                intent=intent_result.intent.value,
                entities=intent_result.entities
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing user input: {str(e)}")
            return AgentResponse(
                text="I encountered an error processing your request. Could you please try again?",
                confidence_score=0.0
            )
    
    async def _handle_system_commands(self, text: str, user_id: str) -> bool:
        """Handle system control commands."""
        
        text_lower = text.lower().strip()
        
        if text_lower in ["stop", "pause", "halt"]:
            self.system_paused = True
            logger.info(f"System paused by user {user_id}")
            return True
        
        elif text_lower in ["resume", "continue", "start"]:
            self.system_paused = False
            logger.info(f"System resumed by user {user_id}")
            return True
        
        elif text_lower in ["help", "assist", "guide"]:
            # This would be handled in response generation
            return False
        
        return False
    
    async def _generate_response(
        self,
        intent_result: IntentResult,
        user_id: str,
        user_context: UserContext,
        original_text: str
    ) -> AgentResponse:
        """Generate appropriate response based on intent."""
        
        # Handle different intent types
        if intent_result.intent == IntentType.UNKNOWN:
            return await self._handle_unknown_intent(original_text, user_context)
        
        elif intent_result.intent == IntentType.GENERAL_QUERY:
            return await self._handle_general_query(original_text, user_context)
        
        elif intent_result.intent == IntentType.SYSTEM_CONTROL:
            return await self._handle_system_control(original_text, user_context)
        
        elif intent_result.intent in [
            IntentType.CALENDAR_CREATE,
            IntentType.CALENDAR_UPDATE,
            IntentType.CALENDAR_DELETE,
            IntentType.CALENDAR_QUERY,
            IntentType.CALENDAR_RESCHEDULE
        ]:
            return await self._handle_calendar_intent(intent_result, user_id, user_context)
        
        elif intent_result.intent in [
            IntentType.TASK_CREATE,
            IntentType.TASK_UPDATE,
            IntentType.TASK_DELETE,
            IntentType.TASK_QUERY,
            IntentType.TASK_COMPLETE
        ]:
            return await self._handle_task_intent(intent_result, user_id, user_context)
        
        elif intent_result.intent in [
            IntentType.MESSAGE_SEND,
            IntentType.MESSAGE_SCHEDULE,
            IntentType.MESSAGE_REMINDER
        ]:
            return await self._handle_message_intent(intent_result, user_id, user_context)
        
        else:
            return AgentResponse(
                text="I understand what you're asking, but I'm not sure how to help with that yet.",
                confidence_score=intent_result.confidence
            )
    
    async def _handle_unknown_intent(
        self,
        text: str,
        user_context: UserContext
    ) -> AgentResponse:
        """Handle unknown or unclear intents."""
        
        clarification_responses = [
            "I'm not sure I understand. Could you be more specific?",
            "Could you rephrase that? I want to make sure I help you correctly.",
            "I didn't quite catch that. What would you like me to help you with?",
            "Can you tell me more about what you'd like to do?"
        ]
        
        # Use conversation history to pick appropriate response
        response_text = clarification_responses[0]  # Default
        
        return AgentResponse(
            text=response_text,
            confidence_score=0.1
        )
    
    async def _handle_general_query(
        self,
        text: str,
        user_context: UserContext
    ) -> AgentResponse:
        """Handle general queries and conversations."""
        
        # This would integrate with a conversational AI model
        # For now, provide a helpful response
        
        if "help" in text.lower():
            help_text = """I can help you with:
• Calendar management (schedule, check, or cancel events)
• Task reminders and to-do lists
• Sending messages via WhatsApp
• Daily planning and organization

Just tell me what you'd like to do in natural language!"""
            
            return AgentResponse(
                text=help_text,
                confidence_score=0.9
            )
        
        return AgentResponse(
            text="I'm here to help with your calendar, tasks, and messages. What can I do for you?",
            confidence_score=0.7
        )
    
    async def _handle_system_control(
        self,
        text: str,
        user_context: UserContext
    ) -> AgentResponse:
        """Handle system control commands."""
        
        if "stop" in text.lower() or "pause" in text.lower():
            return AgentResponse(
                text="I've paused all operations. Say 'resume' when you're ready to continue.",
                confidence_score=1.0
            )
        
        elif "settings" in text.lower() or "preferences" in text.lower():
            return AgentResponse(
                text="You can adjust your settings in the app. What would you like to change?",
                confidence_score=0.8
            )
        
        return AgentResponse(
            text="System command processed.",
            confidence_score=0.5
        )
    
    async def _handle_calendar_intent(
        self,
        intent_result: IntentResult,
        user_id: str,
        user_context: UserContext
    ) -> AgentResponse:
        """Handle calendar-related intents."""
        
        try:
            # Create task plan for calendar operation
            task_plan = await self.task_planner.create_task_plan(
                title=f"Calendar {intent_result.intent.value}",
                description=f"Execute calendar operation: {intent_result.intent.value}",
                user_id=user_id,
                intent_type=intent_result.intent.value,
                entities=intent_result.entities,
                context=intent_result.context
            )
            
            # For queries, execute immediately
            if intent_result.intent == IntentType.CALENDAR_QUERY:
                execution_result = await self.execute_task_plan(task_plan.id)
                
                if execution_result.success:
                    events = []
                    for action in task_plan.actions:
                        if action.result and "events" in action.result:
                            events.extend(action.result["events"])
                    
                    if events:
                        event_list = "\n".join([
                            f"• {event.get('summary', 'Untitled')} at {event.get('start', {}).get('dateTime', 'TBD')}"
                            for event in events[:5]  # Limit to 5 events
                        ])
                        response_text = f"Here are your upcoming events:\n{event_list}"
                    else:
                        response_text = "You don't have any events scheduled for the requested time."
                else:
                    response_text = "I couldn't retrieve your calendar events right now. Please try again."
                
                return AgentResponse(
                    text=response_text,
                    confidence_score=intent_result.confidence,
                    task_plan_id=task_plan.id
                )
            
            # For other operations, check if confirmation is needed
            requires_confirmation = any(action.requires_confirmation for action in task_plan.actions)
            
            if requires_confirmation:
                response_text = self._generate_confirmation_message(intent_result, task_plan)
                return AgentResponse(
                    text=response_text,
                    confidence_score=intent_result.confidence,
                    requires_confirmation=True,
                    task_plan_id=task_plan.id
                )
            else:
                # Execute immediately
                execution_result = await self.execute_task_plan(task_plan.id)
                response_text = self._generate_execution_response(execution_result)
                
                return AgentResponse(
                    text=response_text,
                    confidence_score=intent_result.confidence,
                    task_plan_id=task_plan.id
                )
        
        except Exception as e:
            logger.error(f"Error handling calendar intent: {str(e)}")
            return AgentResponse(
                text="I encountered an issue with your calendar request. Please try again.",
                confidence_score=0.0
            )
    
    async def _handle_task_intent(
        self,
        intent_result: IntentResult,
        user_id: str,
        user_context: UserContext
    ) -> AgentResponse:
        """Handle task-related intents."""
        
        try:
            # Create task plan
            task_plan = await self.task_planner.create_task_plan(
                title=f"Task {intent_result.intent.value}",
                description=f"Execute task operation: {intent_result.intent.value}",
                user_id=user_id,
                intent_type=intent_result.intent.value,
                entities=intent_result.entities,
                context=intent_result.context
            )
            
            # Execute task plan
            execution_result = await self.execute_task_plan(task_plan.id)
            response_text = self._generate_execution_response(execution_result)
            
            return AgentResponse(
                text=response_text,
                confidence_score=intent_result.confidence,
                task_plan_id=task_plan.id
            )
        
        except Exception as e:
            logger.error(f"Error handling task intent: {str(e)}")
            return AgentResponse(
                text="I encountered an issue with your task request. Please try again.",
                confidence_score=0.0
            )
    
    async def _handle_message_intent(
        self,
        intent_result: IntentResult,
        user_id: str,
        user_context: UserContext
    ) -> AgentResponse:
        """Handle messaging-related intents."""
        
        try:
            # Create task plan
            task_plan = await self.task_planner.create_task_plan(
                title=f"Message {intent_result.intent.value}",
                description=f"Execute messaging operation: {intent_result.intent.value}",
                user_id=user_id,
                intent_type=intent_result.intent.value,
                entities=intent_result.entities,
                context=intent_result.context
            )
            
            # Messages typically require confirmation
            requires_confirmation = any(action.requires_confirmation for action in task_plan.actions)
            
            if requires_confirmation:
                response_text = self._generate_confirmation_message(intent_result, task_plan)
                return AgentResponse(
                    text=response_text,
                    confidence_score=intent_result.confidence,
                    requires_confirmation=True,
                    task_plan_id=task_plan.id
                )
            else:
                execution_result = await self.execute_task_plan(task_plan.id)
                response_text = self._generate_execution_response(execution_result)
                
                return AgentResponse(
                    text=response_text,
                    confidence_score=intent_result.confidence,
                    task_plan_id=task_plan.id
                )
        
        except Exception as e:
            logger.error(f"Error handling message intent: {str(e)}")
            return AgentResponse(
                text="I encountered an issue with your message request. Please try again.",
                confidence_score=0.0
            )
    
    def _generate_confirmation_message(
        self,
        intent_result: IntentResult,
        task_plan: TaskPlan
    ) -> str:
        """Generate confirmation message for user."""
        
        intent_messages = {
            IntentType.CALENDAR_CREATE: "create a calendar event",
            IntentType.CALENDAR_DELETE: "delete a calendar event",
            IntentType.MESSAGE_SEND: "send a message",
            IntentType.TASK_CREATE: "create a task reminder"
        }
        
        action_desc = intent_messages.get(intent_result.intent, "perform this action")
        
        # Add specific details from entities
        details = []
        if "title" in intent_result.entities:
            details.append(f"'{intent_result.entities['title']}'")
        if "time" in intent_result.entities:
            details.append(f"at {intent_result.entities['time']}")
        if "people" in intent_result.entities:
            details.append(f"with {', '.join(intent_result.entities['people'])}")
        
        detail_text = " " + " ".join(details) if details else ""
        
        return f"I'm about to {action_desc}{detail_text}. Should I proceed?"
    
    def _generate_execution_response(self, execution_result: ExecutionResult) -> str:
        """Generate response message based on execution result."""
        
        if execution_result.success:
            if execution_result.task_plan.status == TaskStatus.COMPLETED:
                return "Done! I've completed that task for you."
            elif execution_result.task_plan.status == TaskStatus.IN_PROGRESS:
                return "I'm working on that now. I'll let you know when it's complete."
            else:
                return "I've started processing your request."
        else:
            return "I wasn't able to complete that task. Please try again or be more specific."
    
    async def execute_task_plan(self, plan_id: str) -> ExecutionResult:
        """
        Execute a task plan with error recovery.
        
        Args:
            plan_id: Task plan identifier
            
        Returns:
            ExecutionResult with execution details
        """
        
        start_time = datetime.now()
        
        try:
            task_plan = await self.task_planner.execute_task_plan(plan_id)
            
            # Calculate execution metrics
            execution_time = (datetime.now() - start_time).total_seconds()
            
            completed_steps = [
                action.id for action in task_plan.actions 
                if action.status == TaskStatus.COMPLETED
            ]
            
            failed_steps = [
                action.id for action in task_plan.actions 
                if action.status == TaskStatus.FAILED
            ]
            
            success = task_plan.status == TaskStatus.COMPLETED
            
            if success:
                message = "Task plan executed successfully"
            elif task_plan.status == TaskStatus.WAITING_CONFIRMATION:
                message = "Task plan waiting for user confirmation"
            else:
                message = f"Task plan execution incomplete: {task_plan.status}"
            
            return ExecutionResult(
                success=success,
                task_plan=task_plan,
                completed_steps=completed_steps,
                failed_steps=failed_steps,
                message=message,
                execution_time_seconds=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Task plan execution failed: {str(e)}")
            
            return ExecutionResult(
                success=False,
                task_plan=self.task_planner.get_task_plan(plan_id),
                completed_steps=[],
                failed_steps=[],
                message=f"Execution failed: {str(e)}",
                execution_time_seconds=execution_time
            )
    
    async def confirm_task_plan(self, plan_id: str, confirmed: bool) -> AgentResponse:
        """
        Handle user confirmation for a task plan.
        
        Args:
            plan_id: Task plan identifier
            confirmed: Whether user confirmed the action
            
        Returns:
            AgentResponse with confirmation result
        """
        
        task_plan = self.task_planner.get_task_plan(plan_id)
        if not task_plan:
            return AgentResponse(
                text="I couldn't find that task to confirm.",
                confidence_score=0.0
            )
        
        if confirmed:
            # Execute the confirmed task plan
            execution_result = await self.execute_task_plan(plan_id)
            response_text = self._generate_execution_response(execution_result)
        else:
            # Cancel the task plan
            await self.task_planner.cancel_task_plan(plan_id)
            response_text = "Okay, I've cancelled that action."
        
        return AgentResponse(
            text=response_text,
            confidence_score=1.0,
            task_plan_id=plan_id
        )
    
    async def get_daily_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get today's tasks and events for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of today's tasks and events
        """
        
        try:
            # Get user's task plans for today
            user_plans = self.task_planner.get_user_task_plans(user_id)
            
            today_tasks = []
            for plan in user_plans:
                if plan.created_at.date() == datetime.now().date():
                    today_tasks.append({
                        "id": plan.id,
                        "title": plan.title,
                        "status": plan.status.value,
                        "progress": plan.progress,
                        "created_at": plan.created_at.isoformat()
                    })
            
            return today_tasks
            
        except Exception as e:
            logger.error(f"Error getting daily tasks: {str(e)}")
            return []
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        
        service_status = await self.action_executor.get_service_status()
        
        return {
            "system_paused": self.system_paused,
            "active_sessions": len(self.active_sessions),
            "active_task_plans": len(self.task_planner.active_plans),
            "services": service_status,
            "timestamp": datetime.now().isoformat()
        }