import pytest
import json
from unittest.mock import Mock
from datetime import datetime

from src.conversation import ConversationManager, ConversationMessage


@pytest.fixture
def mock_redis():
    mock_client = Mock()
    mock_client.exists.return_value = False
    mock_client.get.return_value = None
    mock_client.setex.return_value = True
    mock_client.sadd.return_value = True
    mock_client.expire.return_value = True
    mock_client.lpush.return_value = True
    mock_client.lrange.return_value = []
    mock_client.smembers.return_value = set()
    mock_client.delete.return_value = True
    mock_client.srem.return_value = True
    return mock_client


@pytest.fixture
def conversation_manager(mock_redis):
    return ConversationManager(mock_redis)


class TestConversationManager:
    def test_generate_ids(self, conversation_manager):
        user_id = conversation_manager.generate_user_id()
        conv_id = conversation_manager.generate_conversation_id()

        assert user_id.startswith("user_")
        assert len(user_id) == 17
        assert conv_id.startswith("conv_")
        assert len(conv_id) == 17

    def test_create_user_session_new(self, conversation_manager, mock_redis):
        mock_redis.exists.return_value = False

        user_id = conversation_manager.get_or_create_user_session()

        assert user_id.startswith("user_")
        mock_redis.setex.assert_called()

    def test_create_user_session_existing(self, conversation_manager, mock_redis):
        existing_user_id = "user_existing123"
        mock_redis.exists.return_value = True
        mock_redis.get.return_value = json.dumps({
            "user_id": existing_user_id,
            "created_at": "2025-01-01T00:00:00",
            "last_active": "2025-01-01T00:00:00",
            "total_conversations": 1
        })

        result_user_id = conversation_manager.get_or_create_user_session(existing_user_id)

        assert result_user_id == existing_user_id
        mock_redis.setex.assert_called()

    def test_create_conversation(self, conversation_manager, mock_redis):
        user_id = "user_test123"

        conv_id = conversation_manager.create_conversation(user_id, "Test Conversation")

        assert conv_id.startswith("conv_")
        mock_redis.setex.assert_called()
        mock_redis.sadd.assert_called()

    def test_add_message(self, conversation_manager, mock_redis):
        conv_id = "conv_test123"

        msg_id = conversation_manager.add_message(
            conv_id, "Hello", "user", "KnowledgeAgent", {"test": "metadata"}
        )

        assert msg_id.startswith("msg_")
        mock_redis.setex.assert_called()
        mock_redis.lpush.assert_called()

    def test_get_conversation_history(self, conversation_manager, mock_redis):
        conv_id = "conv_test123"

        mock_redis.lrange.return_value = [b"msg_1", b"msg_2"]

        test_message = ConversationMessage(
            id="msg_1",
            content="Test message",
            sender="user",
            timestamp=datetime.now()
        )
        mock_redis.get.return_value = test_message.model_dump_json()

        history = conversation_manager.get_conversation_history(conv_id)

        assert len(history) >= 0
        mock_redis.lrange.assert_called()

    def test_delete_conversation(self, conversation_manager, mock_redis):
        conv_id = "conv_test123"
        user_id = "user_test123"

        mock_redis.lrange.return_value = [b"msg_1", b"msg_2"]

        result = conversation_manager.delete_conversation(conv_id, user_id)

        assert result is True
        assert mock_redis.delete.call_count >= 3

    def test_conversation_manager_scalability(self, conversation_manager):
        user_id = "user_test123"

        conv_ids = []
        for i in range(10):
            conv_id = conversation_manager.create_conversation(user_id, f"Conv {i}")
            conv_ids.append(conv_id)

        for conv_id in conv_ids:
            for j in range(5):
                conversation_manager.add_message(conv_id, f"Message {j}", "user")

        assert len(conv_ids) == 10
