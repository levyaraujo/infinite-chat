import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.agent import MathAgent


class TestMathAgent:
    @pytest.fixture
    def math_agent(self):
        with patch.dict('os.environ', {'OLLAMA_BASE_URL': 'http://test:11434'}):
            return MathAgent()

    def test_build_llm_payload_structure(self, math_agent):
        query = "What is 5 + 3?"
        payload = math_agent.build_llm_payload(query, stream=True)

        assert payload["model"] == "llama3.2"
        assert payload["stream"] is True
        assert "options" in payload
        assert payload["options"]["temperature"] == 0.1
        assert query in payload["prompt"]
        assert "matemática" in payload["prompt"]

    def test_build_llm_payload_content(self, math_agent):
        query = "Calculate 10 * 2"
        payload = math_agent.build_llm_payload(query, stream=False)

        prompt = payload["prompt"]
        assert "especialista em matemática" in prompt
        assert query in prompt
        assert "português brasileiro" in prompt
        assert "resposta final" in prompt.lower()

    @pytest.mark.asyncio
    async def test_process_math_query(self, math_agent):
        with patch.object(math_agent, 'call_llm') as mock_call_llm:
            mock_call_llm.return_value = AsyncMock()
            mock_call_llm.return_value.__aiter__.return_value = [
                "Para", " calcular", " 5 + 3", " = 8"
            ]

            results = []
            async for result in math_agent.process("5 + 3", "conv123", "user456"):
                results.append(result)

            assert len(results) >= 2

            assert results[0]["type"] == "sources"
            assert "sources" in results[0]["data"]

            chunk_results = [r for r in results if r["type"] == "chunk"]
            assert len(chunk_results) > 0
            assert all(r["data"]["agent"] == "MathAgent" for r in chunk_results)

    @pytest.mark.asyncio
    async def test_math_expressions(self, math_agent):
        expressions = [
            "65 x 3.11",
            "70 + 12",
            "(42 * 2) / 6",
            "√25",
            "10^2"
        ]

        for expr in expressions:
            payload = math_agent.build_llm_payload(expr)
            assert expr in payload["prompt"]
            assert payload["model"] == "llama3.2"
