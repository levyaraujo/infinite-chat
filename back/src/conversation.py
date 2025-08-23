import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import redis
from pydantic import BaseModel

class ConversationMessage(BaseModel):
    id: str
    content: str
    sender: str
    agent: Optional[str] = None
    timestamp: datetime
    metadata: Optional[Dict] = None

class ConversationManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.user_conversations_prefix = "user_conversations:"
        self.conversation_prefix = "conversation:"
        self.message_prefix = "message:"
        self.user_session_prefix = "user_session:"

    def generate_user_id(self) -> str:
        """Generate a unique user ID"""
        return f"user_{uuid.uuid4().hex[:12]}"

    def generate_conversation_id(self) -> str:
        """Generate a unique conversation ID"""
        return f"conv_{uuid.uuid4().hex[:12]}"

    def get_or_create_user_session(self, user_id: Optional[str] = None) -> str:
        """Get existing user session or create new one"""
        if not user_id:
            user_id = self.generate_user_id()

        session_key = f"{self.user_session_prefix}{user_id}"

        if not self.redis.exists(session_key):
            session_data = {
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat(),
                "total_conversations": 0
            }
            self.redis.setex(
                session_key,
                timedelta(days=30),
                json.dumps(session_data)
            )
        else:

            session_data = json.loads(self.redis.get(session_key))
            session_data["last_active"] = datetime.now().isoformat()
            self.redis.setex(session_key, timedelta(days=30), json.dumps(session_data))

        return user_id

    def create_conversation(self, user_id: str, title: Optional[str] = None) -> str:
        """Create a new conversation for user"""
        conversation_id = self.generate_conversation_id()

        conversation_data = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "title": title or "Nova Conversa",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "message_count": 0,
            "last_message": None
        }

        conv_key = f"{self.conversation_prefix}{conversation_id}"
        self.redis.setex(conv_key, timedelta(days=30), json.dumps(conversation_data))

        user_conv_key = f"{self.user_conversations_prefix}{user_id}"
        self.redis.sadd(user_conv_key, conversation_id)
        self.redis.expire(user_conv_key, timedelta(days=30))

        session_key = f"{self.user_session_prefix}{user_id}"
        if self.redis.exists(session_key):
            session_data = json.loads(self.redis.get(session_key))
            session_data["total_conversations"] = session_data.get("total_conversations", 0) + 1
            self.redis.setex(session_key, timedelta(days=30), json.dumps(session_data))

        return conversation_id

    def add_message(self, conversation_id: str, content: str, sender: str,
                    agent: Optional[str] = None, metadata: Optional[Dict] = None) -> str:
        """Add a message to conversation"""
        message_id = f"msg_{uuid.uuid4().hex[:12]}"

        message = ConversationMessage(
            id=message_id,
            content=content,
            sender=sender,
            agent=agent,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )

        msg_key = f"{self.message_prefix}{message_id}"
        self.redis.setex(
            msg_key,
            timedelta(days=30),
            message.model_dump_json()
        )

        conv_messages_key = f"{self.conversation_prefix}{conversation_id}:messages"
        self.redis.lpush(conv_messages_key, message_id)
        self.redis.expire(conv_messages_key, timedelta(days=30))

        conv_key = f"{self.conversation_prefix}{conversation_id}"
        if self.redis.exists(conv_key):
            conv_data = json.loads(self.redis.get(conv_key))
            conv_data["updated_at"] = datetime.now().isoformat()
            conv_data["message_count"] = conv_data.get("message_count", 0) + 1
            conv_data["last_message"] = content[:100] + "..." if len(content) > 100 else content

            if conv_data["message_count"] == 1 and sender == "user":
                conv_data["title"] = content[:50] + "..." if len(content) > 50 else content

            self.redis.setex(conv_key, timedelta(days=30), json.dumps(conv_data))

        return message_id

    def get_conversation_history(self, conversation_id: str, limit: int = 50) -> List[ConversationMessage]:
        """Get conversation message history"""
        conv_messages_key = f"{self.conversation_prefix}{conversation_id}:messages"
        message_ids = self.redis.lrange(conv_messages_key, 0, limit - 1)

        messages = []
        for msg_id in reversed(message_ids):
            msg_key = f"{self.message_prefix}{msg_id.decode()}"
            msg_data = self.redis.get(msg_key)
            if msg_data:
                message = ConversationMessage.model_validate_json(msg_data)
                messages.append(message)

        return messages

    def get_user_conversations(self, user_id: str) -> List[Dict]:
        """Get all conversations for a user"""
        user_conv_key = f"{self.user_conversations_prefix}{user_id}"
        conversation_ids = self.redis.smembers(user_conv_key)

        conversations = []
        for conv_id in conversation_ids:
            conv_key = f"{self.conversation_prefix}{conv_id.decode()}"
            conv_data = self.redis.get(conv_key)
            if conv_data:
                conversations.append(json.loads(conv_data))

        conversations.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return conversations

    def get_conversation_info(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation metadata"""
        conv_key = f"{self.conversation_prefix}{conversation_id}"
        conv_data = self.redis.get(conv_key)
        return json.loads(conv_data) if conv_data else None

    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Delete a conversation and all its messages"""
        try:

            conv_messages_key = f"{self.conversation_prefix}{conversation_id}:messages"
            message_ids = self.redis.lrange(conv_messages_key, 0, -1)

            for msg_id in message_ids:
                msg_key = f"{self.message_prefix}{msg_id.decode()}"
                self.redis.delete(msg_key)

            self.redis.delete(conv_messages_key)

            conv_key = f"{self.conversation_prefix}{conversation_id}"
            self.redis.delete(conv_key)

            user_conv_key = f"{self.user_conversations_prefix}{user_id}"
            self.redis.srem(user_conv_key, conversation_id)

            return True
        except Exception:
            return False

    def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """Update conversation title"""
        conv_key = f"{self.conversation_prefix}{conversation_id}"
        if self.redis.exists(conv_key):
            conv_data = json.loads(self.redis.get(conv_key))
            conv_data["title"] = title
            conv_data["updated_at"] = datetime.now().isoformat()
            self.redis.setex(conv_key, timedelta(days=30), json.dumps(conv_data))
            return True
        return False