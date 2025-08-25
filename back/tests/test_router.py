import pytest
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


class TestRouterAgent:
    def test_classify_math_keywords(self, router_agent):
        math_queries = [
            "Quanto é 5 + 3?",
            "Calcule 10 * 2",
            "Resolva essa equação: x + 5 = 10",
            "Qual o resultado da divisão de 20 por 4?",
            "Preciso de uma calculadora matemática",
            "Como resolver essa soma: 15 + 25?"
        ]

        for query in math_queries:
            result = router_agent.classify(query, "test_conv", "test_user")
            assert result == AgentType.MATH, f"Query '{query}' should route to MathAgent"

    def test_classify_math_symbols(self, router_agent):
        math_queries = [
            "65 * 3.11",
            "70 + 12",
            "(42 * 2) / 6",
            "100 - 25 = ?",
            "√16",
            "25%"
        ]

        for query in math_queries:
            result = router_agent.classify(query, "test_conv", "test_user")
            assert result == AgentType.MATH, f"Query '{query}' should route to MathAgent"

    def test_classify_knowledge_queries(self, router_agent):
        knowledge_queries = [
            "Qual a taxa da maquininha?",
            "Como cadastrar minha conta?",
            "Posso usar meu telefone como maquininha?",
            "Quais são os horários de atendimento?",
            "Como entrar em contato com o suporte?",
            "Preciso de ajuda com meu produto"
        ]

        for query in knowledge_queries:
            result = router_agent.classify(query, "test_conv", "test_user")
            assert result == AgentType.KNOWLEDGE, f"Query '{query}' should route to KnowledgeAgent"

    def test_classify_edge_cases(self, router_agent):
        edge_cases = [
            ("", AgentType.KNOWLEDGE),
            ("   ", AgentType.KNOWLEDGE),
            ("Math is hard", AgentType.KNOWLEDGE),
            ("I need help with support", AgentType.KNOWLEDGE),
            ("Calculate my fees", AgentType.MATH),
        ]

        for query, expected in edge_cases:
            result = router_agent.classify(query, "test_conv", "test_user")
            assert result == expected, f"Query '{query}' should route to {expected.value}"
