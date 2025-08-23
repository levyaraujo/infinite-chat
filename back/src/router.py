import traceback
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import re

import httpx

from infra.logs import setup_logging, log_agent_execution
from src.agent import Agent, MathAgent, KnowledgeAgent
from src.rag.retriever import RAGRetriever

logger = setup_logging()

class AgentType(Enum):
    MATH = "math"
    KNOWLEDGE = "knowledge"

@asynccontextmanager
async def conversation_session(conversation_manager, user_id: Optional[str] = None):
    """Context manager for handling conversation sessions"""
    try:
        current_user_id = conversation_manager.get_or_create_user_session(user_id)
        yield current_user_id
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error in conversation session: {e}")
        raise

class RouterAgent:
    def __init__(self, rag_retriever, conversation_manager):
        self.rag_retriever = rag_retriever
        self.conversation_manager = conversation_manager
        self.agents = {
            AgentType.KNOWLEDGE: KnowledgeAgent(rag_retriever),
            AgentType.MATH: MathAgent()
        }

    def classify(self, query: str, conversation_id: str = None, user_id: str = None) -> AgentType:
        """
        A very simple math query classifier based on keywords and symbols.
        This can be improved with a more sophisticated NLP model if needed or using LLM.
        If no math indicators are found, defaults to KNOWLEDGE agent.
        """
        start_time = time.time()
        query_lower = query.lower()

        math_keywords = ["calcul", "matemática", "soma", "subtração", "multiplicação",
                         "divisão", "equação", "resolver", "resultado", "quanto é", "raiz quadrada",
                         "cálculo", "matemático", "matemáticos", "diferencial", "integral"]
        math_symbols = ["+", "-", "*", "/", "=", "^", "√", "%"]

        agent = AgentType.KNOWLEDGE

        if any(keyword in query_lower for keyword in math_keywords) or \
                any(symbol in query for symbol in math_symbols):
            agent = AgentType.MATH

        execution_time = time.time() - start_time

        decision = f"Routing to {agent.value} agent based on query analysis"

        log_agent_execution(
            logger=logger,
            agent_name="RouterAgent",
            conversation_id=conversation_id or "unknown",
            user_id=user_id or "unknown",
            execution_time=execution_time,
            decision=decision,
            processed_content=query[:200] + "..." if len(query) > 200 else query
        )

        return agent