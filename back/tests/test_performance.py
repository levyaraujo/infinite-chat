import pytest
import time
from unittest.mock import Mock, patch

from src.router import RouterAgent, AgentType
from src.conversation import ConversationManager


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
def mock_rag_retriever():
    mock_retriever = Mock()
    mock_vectorstore = Mock()
    mock_retriever_obj = Mock()
    mock_vectorstore.as_retriever.return_value = mock_retriever_obj
    mock_retriever.vectorstore = mock_vectorstore
    return mock_retriever


@pytest.fixture
def conversation_manager(mock_redis):
    return ConversationManager(mock_redis)


@pytest.fixture
def router_agent(mock_rag_retriever, conversation_manager):
    with patch('src.router.KnowledgeAgent') as mock_knowledge_agent:
        mock_knowledge_agent.return_value = Mock()
        return RouterAgent(mock_rag_retriever, conversation_manager)


class TestPerformance:
    @pytest.mark.asyncio
    async def test_router_classification_speed(self, router_agent):
        query = "What is 5 + 3?"

        start_time = time.time()
        result = router_agent.classify(query, "conv123", "user456")
        end_time = time.time()

        assert result == AgentType.MATH
        assert (end_time - start_time) < 0.1
