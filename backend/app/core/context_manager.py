"""
Context Manager for the Agentic Core.

This module manages conversation state, user context, and contextual memory
to enable context-aware AI interactions and decision making.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ContextType(str, Enum):
    """Types of context information."""
    
    USER_PROFILE = "user_profile"
    CONVERSATION = "conversation"
    CALENDAR = "calendar"
    TASKS = "tasks"
    PREFERENCES = "preferences"
    LOCATION = "location"
    TEMPORAL = "temporal"


@dataclass
class ContextItem:
    """Individual context item with metadata."""
    
    key: str
    value: Any
    context_type: ContextType
    timestamp: datetime
    expires_at: Optional[datetime] = None
    confidence: float = 1.0
    source: str = "system"


@dataclass
class UserContext:
    """Complete user context information."""
    
    user_id: str
    profile: Dict[str, Any]
    preferences: Dict[str, Any]
    current_location: Optional[Dict[str, Any]] = None
    timezone: str = "UTC"
    language: str = "en-US"
    active_session: bool = False


class ContextManager:
    """
    Manages contextual information for intelligent AI interactions.
    
    Provides context awareness and conversation state management
    to enable personalized and coherent AI responses.
    """
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.context_store: Dict[str, Dict[str, ContextItem]] = {}
        self.user_contexts: Dict[str, UserContext] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}
        
        # Context retention policies (in hours)
        self.retention_policies = {
            ContextType.CONVERSATION: 24,
            ContextType.CALENDAR: 168,  # 1 week
            ContextType.TASKS: 720,     # 1 month
            ContextType.PREFERENCES: 8760,  # 1 year
            ContextType.LOCATION: 1,
            ContextType.TEMPORAL: 24,
            ContextType.USER_PROFILE: 8760
        }
    
    async def get_user_context(self, user_id: str) -> UserContext:
        """
        Get complete user context information.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            UserContext object with all relevant user information
        """
        
        if user_id in self.user_contexts:
            return self.user_contexts[user_id]
        
        # Load from persistent storage if available
        context = await self._load_user_context(user_id)
        if context:
            self.user_contexts[user_id] = context
            return context
        
        # Create default context
        default_context = UserContext(
            user_id=user_id,
            profile={},
            preferences={
                "language": "en-US",
                "timezone": "UTC",
                "notification_preferences": {},
                "privacy_level": "standard"
            }
        )
        
        self.user_contexts[user_id] = default_context
        return default_context
    
    async def update_user_context(
        self, 
        user_id: str, 
        updates: Dict[str, Any],
        context_type: ContextType = ContextType.USER_PROFILE
    ) -> None:
        """
        Update user context information.
        
        Args:
            user_id: Unique identifier for the user
            updates: Dictionary of updates to apply
            context_type: Type of context being updated
        """
        
        user_context = await self.get_user_context(user_id)
        
        # Apply updates based on context type
        if context_type == ContextType.USER_PROFILE:
            user_context.profile.update(updates)
        elif context_type == ContextType.PREFERENCES:
            user_context.preferences.update(updates)
        elif context_type == ContextType.LOCATION:
            user_context.current_location = updates
        
        # Store individual context items
        for key, value in updates.items():
            await self.set_context(
                user_id=user_id,
                key=key,
                value=value,
                context_type=context_type
            )
        
        # Persist changes
        await self._save_user_context(user_id, user_context)
        
        logger.info(f"Updated {context_type.value} context for user {user_id}")
    
    async def set_context(
        self,
        user_id: str,
        key: str,
        value: Any,
        context_type: ContextType,
        expires_in_hours: Optional[int] = None,
        confidence: float = 1.0,
        source: str = "system"
    ) -> None:
        """
        Set a specific context item.
        
        Args:
            user_id: Unique identifier for the user
            key: Context key
            value: Context value
            context_type: Type of context
            expires_in_hours: Optional expiration time in hours
            confidence: Confidence level of the context item
            source: Source of the context information
        """
        
        if user_id not in self.context_store:
            self.context_store[user_id] = {}
        
        # Calculate expiration time
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        elif context_type in self.retention_policies:
            expires_at = datetime.now() + timedelta(hours=self.retention_policies[context_type])
        
        # Create context item
        context_item = ContextItem(
            key=key,
            value=value,
            context_type=context_type,
            timestamp=datetime.now(),
            expires_at=expires_at,
            confidence=confidence,
            source=source
        )
        
        self.context_store[user_id][key] = context_item
        
        # Persist to Redis if available
        if self.redis_client:
            await self._persist_context_item(user_id, key, context_item)
    
    async def get_context(
        self,
        user_id: str,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Get a specific context item.
        
        Args:
            user_id: Unique identifier for the user
            key: Context key to retrieve
            default: Default value if key not found
            
        Returns:
            Context value or default
        """
        
        if user_id not in self.context_store:
            return default
        
        context_item = self.context_store[user_id].get(key)
        if not context_item:
            return default
        
        # Check if context has expired
        if context_item.expires_at and datetime.now() > context_item.expires_at:
            await self.remove_context(user_id, key)
            return default
        
        return context_item.value
    
    async def get_context_by_type(
        self,
        user_id: str,
        context_type: ContextType
    ) -> Dict[str, Any]:
        """
        Get all context items of a specific type.
        
        Args:
            user_id: Unique identifier for the user
            context_type: Type of context to retrieve
            
        Returns:
            Dictionary of context items
        """
        
        if user_id not in self.context_store:
            return {}
        
        result = {}
        current_time = datetime.now()
        
        for key, context_item in self.context_store[user_id].items():
            # Skip expired items
            if context_item.expires_at and current_time > context_item.expires_at:
                continue
            
            if context_item.context_type == context_type:
                result[key] = context_item.value
        
        return result
    
    async def remove_context(self, user_id: str, key: str) -> bool:
        """
        Remove a specific context item.
        
        Args:
            user_id: Unique identifier for the user
            key: Context key to remove
            
        Returns:
            True if item was removed, False if not found
        """
        
        if user_id not in self.context_store:
            return False
        
        if key in self.context_store[user_id]:
            del self.context_store[user_id][key]
            
            # Remove from Redis if available
            if self.redis_client:
                await self._remove_persisted_context(user_id, key)
            
            return True
        
        return False
    
    async def clear_user_context(self, user_id: str) -> None:
        """
        Clear all context for a user.
        
        Args:
            user_id: Unique identifier for the user
        """
        
        if user_id in self.context_store:
            del self.context_store[user_id]
        
        if user_id in self.user_contexts:
            del self.user_contexts[user_id]
        
        if user_id in self.session_data:
            del self.session_data[user_id]
        
        # Clear from Redis if available
        if self.redis_client:
            await self._clear_persisted_context(user_id)
        
        logger.info(f"Cleared all context for user {user_id}")
    
    async def cleanup_expired_context(self) -> int:
        """
        Clean up expired context items.
        
        Returns:
            Number of items cleaned up
        """
        
        cleaned_count = 0
        current_time = datetime.now()
        
        for user_id in list(self.context_store.keys()):
            user_context = self.context_store[user_id]
            expired_keys = []
            
            for key, context_item in user_context.items():
                if context_item.expires_at and current_time > context_item.expires_at:
                    expired_keys.append(key)
            
            for key in expired_keys:
                await self.remove_context(user_id, key)
                cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} expired context items")
        return cleaned_count
    
    async def get_conversation_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for context.
        
        Args:
            user_id: Unique identifier for the user
            limit: Maximum number of history items to return
            
        Returns:
            List of conversation history items
        """
        
        history = await self.get_context(user_id, "conversation_history", [])
        
        if isinstance(history, list):
            return history[-limit:] if len(history) > limit else history
        
        return []
    
    async def add_conversation_turn(
        self,
        user_id: str,
        user_input: str,
        ai_response: str,
        intent: str,
        entities: Dict[str, Any]
    ) -> None:
        """
        Add a conversation turn to history.
        
        Args:
            user_id: Unique identifier for the user
            user_input: User's input text
            ai_response: AI's response text
            intent: Recognized intent
            entities: Extracted entities
        """
        
        history = await self.get_conversation_history(user_id)
        
        turn = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "ai_response": ai_response,
            "intent": intent,
            "entities": entities
        }
        
        history.append(turn)
        
        # Keep only last 20 turns
        if len(history) > 20:
            history = history[-20:]
        
        await self.set_context(
            user_id=user_id,
            key="conversation_history",
            value=history,
            context_type=ContextType.CONVERSATION
        )
    
    async def get_contextual_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get a summary of all relevant context for the user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Dictionary containing contextual summary
        """
        
        user_context = await self.get_user_context(user_id)
        
        summary = {
            "user_profile": user_context.profile,
            "preferences": user_context.preferences,
            "current_location": user_context.current_location,
            "timezone": user_context.timezone,
            "language": user_context.language,
            "recent_conversations": await self.get_conversation_history(user_id, 5),
            "calendar_context": await self.get_context_by_type(user_id, ContextType.CALENDAR),
            "task_context": await self.get_context_by_type(user_id, ContextType.TASKS),
            "temporal_context": await self.get_context_by_type(user_id, ContextType.TEMPORAL)
        }
        
        return summary
    
    async def _load_user_context(self, user_id: str) -> Optional[UserContext]:
        """Load user context from persistent storage."""
        
        if not self.redis_client:
            return None
        
        try:
            context_data = await self.redis_client.get(f"user_context:{user_id}")
            if context_data:
                data = json.loads(context_data)
                return UserContext(**data)
        except Exception as e:
            logger.error(f"Error loading user context: {str(e)}")
        
        return None
    
    async def _save_user_context(self, user_id: str, context: UserContext) -> None:
        """Save user context to persistent storage."""
        
        if not self.redis_client:
            return
        
        try:
            context_data = json.dumps(asdict(context), default=str)
            await self.redis_client.setex(
                f"user_context:{user_id}",
                86400 * 7,  # 7 days
                context_data
            )
        except Exception as e:
            logger.error(f"Error saving user context: {str(e)}")
    
    async def _persist_context_item(
        self,
        user_id: str,
        key: str,
        context_item: ContextItem
    ) -> None:
        """Persist individual context item to Redis."""
        
        try:
            item_data = json.dumps(asdict(context_item), default=str)
            redis_key = f"context:{user_id}:{key}"
            
            if context_item.expires_at:
                ttl = int((context_item.expires_at - datetime.now()).total_seconds())
                await self.redis_client.setex(redis_key, ttl, item_data)
            else:
                await self.redis_client.set(redis_key, item_data)
                
        except Exception as e:
            logger.error(f"Error persisting context item: {str(e)}")
    
    async def _remove_persisted_context(self, user_id: str, key: str) -> None:
        """Remove persisted context item from Redis."""
        
        try:
            await self.redis_client.delete(f"context:{user_id}:{key}")
        except Exception as e:
            logger.error(f"Error removing persisted context: {str(e)}")
    
    async def _clear_persisted_context(self, user_id: str) -> None:
        """Clear all persisted context for a user from Redis."""
        
        try:
            # Get all keys for this user
            pattern = f"context:{user_id}:*"
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                await self.redis_client.delete(*keys)
            
            # Also clear user context
            await self.redis_client.delete(f"user_context:{user_id}")
            
        except Exception as e:
            logger.error(f"Error clearing persisted context: {str(e)}")