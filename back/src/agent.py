import json
import os
import time
from typing import Dict, List

import httpx
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import OllamaLLM

from infra.logs import setup_logging, log_agent_execution
from src.rag.retriever import RAGRetriever

logger = setup_logging()


class Agent:
    def __init__(self):
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.__llm = ollama_base_url

    async def call_llm(self, payload):
        timeout = httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream('POST', f"{self.__llm}/api/generate", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                data = json.loads(line)
                                if 'response' in data:
                                    yield data['response']
                                if data.get('done', False):
                                    break
                            except json.JSONDecodeError:
                                continue
        except httpx.ReadTimeout:
            raise Exception("Timeout error: The LLM is taking too long to respond.")
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"Unexpected error: {e}")


class KnowledgeAgent(Agent):
    def __init__(self, rag: RAGRetriever):
        super().__init__()
        self.retriever = rag
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.llm = OllamaLLM(
            model="llama3.2",
            base_url=ollama_base_url,
            temperature=0.2,
            top_p=0.9,
            repeat_penalty=1.1,
            num_ctx=4096
        )
        self.vectorstore = rag.vectorstore
        self.prompt = ChatPromptTemplate.from_template("""
            Você é um assistente virtual amigável e prestativo da InfinitePay! Seu objetivo é ajudar os clientes com suas dúvidas de forma clara, objetiva e acolhedora.
            
            Question: {question}
            Context: {context}


            INSTRUÇÕES CRÍTICAS:
            - Use EXCLUSIVAMENTE as informações fornecidas para construir sua resposta
            - NÃO repita ou parafraseie a pergunta do cliente
            - Se há passos numerados ou instruções no contexto, organize-os claramente na resposta
            - Seja completo e detalhado quando as informações estão disponíveis
            - Seja sempre simpático e use uma linguagem acessível
            - Use emojis quando apropriado para deixar a conversa mais amigável
            - Não mencione "documentos", "fontes" ou "base de conhecimento"
            - APENAS se não houver informação relevante responda: "Não tenho essa informação específica no momento."
            - Sempre termine oferecendo ajuda adicional

            Baseado nas informações fornecidas acima, responda de forma completa e amigável:
            """)

        def format_docs(docs):
            """Format documents for the QA chain"""
            return "\n\n".join(doc.page_content for doc in docs)

        self.qa_chain = (
                {
                    "context": self.vectorstore.as_retriever() | format_docs,
                    "question": RunnablePassthrough(),
                }
                | self.prompt
                | self.llm
                | StrOutputParser()
        )

    async def build_llm_payload(self, query: str, stream: bool = True, sources: List[Document] = None) -> Dict:
        """
        Build the payload for the LLM and add personality to the response.
        :param query:
        :param stream:
        :param sources:
        :return:
        """

        if not sources or len(sources) == 0:
            context = "Não foram encontrados documentos relevantes na base de conhecimento."
        else:
            context_parts = []
            for i, result in enumerate(sources):
                context_parts.append(
                    f"{result.metadata.get('source_url')} - {result.metadata.get('original_title')}\n\n{result.page_content}\n")
            context = "\n".join(context_parts)

        prompt = f"""Você é um assistente virtual amigável e prestativo da InfinitePay! Seu objetivo é ajudar os clientes com suas dúvidas de forma clara, objetiva e acolhedora.

        PERGUNTA DO CLIENTE: {query}

        INFORMAÇÕES DISPONÍVEIS PARA RESPONDER:
        {context}

        INSTRUÇÕES CRÍTICAS:
        - As informações acima contêm a resposta para a pergunta do cliente
        - Use EXCLUSIVAMENTE essas informações para construir sua resposta e todo o contexto relacionado
        - NÃO repita ou parafraseie a pergunta do cliente
        - Se há passos numerados ou instruções no contexto, organize-os claramente na resposta
        - Seja completo e detalhado quando as informações estão disponíveis
        - Seja sempre simpático e use uma linguagem acessível
        - Use emojis quando apropriado para deixar a conversa mais amigável
        - Não mencione "documentos", "fontes" ou "base de conhecimento"
        - APENAS se não houver informação relevante responda: "Não tenho essa informação específica no momento."
        - Sempre termine oferecendo ajuda adicional

        Baseado nas informações fornecidas acima, responda de forma completa e amigável:"""

        payload = {
            "model": "llama3.2",
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
                "num_ctx": 4096
            }
        }

        return payload

    async def process(self, query: str, conversation_id: str = None, user_id: str = None):
        """Process query using LangChain QA chain"""
        start = time.time()

        if not self.vectorstore:
            async for result in self.process_for_stream(query, conversation_id, user_id):
                yield result
            return

        try:
            retriever = self.vectorstore.as_retriever()
            sources = await retriever.ainvoke(query) if hasattr(retriever, 'ainvoke') else retriever.invoke(query)

            if sources:
                source_names = set(source.metadata.get("source", "Documento") for source in sources)

                yield {
                    "type": "sources",
                    "data": {
                        "sources": list(source_names),
                        "documents_found": len(sources)
                    }
                }

                response = await self.qa_chain.ainvoke(query)

                yield {
                    "type": "chunk",
                    "data": {
                        "content": response,
                        "agent": "KnowledgeAgent"
                    }
                }

                execution_time = time.time() - start

                log_agent_execution(
                    logger=logger,
                    agent_name="KnowledgeAgent",
                    conversation_id=conversation_id or "unknown",
                    user_id=user_id or "unknown",
                    execution_time=execution_time,
                    processed_content=f"Query: {query[:100]}... Response: {response[:300]}...",
                    decision=f"QA Chain processed {len(sources)} documents from sources: {', '.join(list(source_names)[:3])}"
                )
            else:
                no_info_response = "Desculpe, não encontrei informações relevantes na minha base de conhecimento sobre essa pergunta. Posso ajudar com outras dúvidas sobre InfinitePay?"

                yield {
                    "type": "sources",
                    "data": {
                        "sources": [],
                        "documents_found": 0
                    }
                }

                yield {
                    "type": "chunk",
                    "data": {
                        "content": no_info_response,
                        "agent": "KnowledgeAgent"
                    }
                }

                execution_time = time.time() - start

                log_agent_execution(
                    logger=logger,
                    agent_name="KnowledgeAgent",
                    conversation_id=conversation_id or "unknown",
                    user_id=user_id or "unknown",
                    execution_time=execution_time,
                    processed_content=f"Query: {query[:100]}... No relevant documents found",
                    decision="No relevant documents found in knowledge base"
                )

        except Exception as e:
            logger.error(f"Error in QA chain processing: {e}")
            async for result in self.process_for_stream(query, conversation_id, user_id):
                yield result

    async def process_for_stream(self, query: str, conversation_id: str = None, user_id: str = None):
        """Process query and yield streaming responses"""
        start = time.time()
        full_response = ""

        sources: List[Document] = await self.retriever.search_by_distance(query=query)

        print(f"SOURCES FOUND: {len(sources)}")

        if sources:
            source_names = set(source.metadata.get("source", "Documento") for source in sources)

            yield {
                "type": "sources",
                "data": {
                    "sources": list(source_names),
                    "documents_found": len(sources)
                }
            }

            payload = await self.build_llm_payload(query=query, stream=True, sources=sources)

            async for chunk in self.call_llm(payload):
                full_response += chunk
                yield {
                    "type": "chunk",
                    "data": {
                        "content": chunk,
                        "agent": "KnowledgeAgent"
                    }
                }

            execution_time = time.time() - start

            log_agent_execution(
                logger=logger,
                agent_name="KnowledgeAgent",
                conversation_id=conversation_id or "unknown",
                user_id=user_id or "unknown",
                execution_time=execution_time,
                processed_content=f"Query: {query[:100]}... Response: {full_response[:300]}...",
                decision=f"Retrieved {len(sources)} documents from sources: {', '.join(list(source_names)[:3])}"
            )
        else:
            no_info_response = (
                "Desculpe, não encontrei informações relevantes na minha base de conhecimento sobre essa"
                " pergunta. Posso ajudar com outras dúvidas sobre InfinitePay?"
            )

            yield {
                "type": "sources",
                "data": {
                    "sources": [],
                    "documents_found": 0
                }
            }

            yield {
                "type": "chunk",
                "data": {
                    "content": no_info_response,
                    "agent": "KnowledgeAgent"
                }
            }

            execution_time = time.time() - start

            log_agent_execution(
                logger=logger,
                agent_name="KnowledgeAgent",
                conversation_id=conversation_id or "unknown",
                user_id=user_id or "unknown",
                execution_time=execution_time,
                processed_content=f"Query: {query[:100]}... No relevant documents found",
                decision="No relevant documents found in knowledge base"
            )


class MathAgent(Agent):
    def __init__(self):
        super().__init__()

    def build_llm_payload(self, query: str, stream: bool = True) -> Dict:
        prompt = f"""Você é um especialista em matemática. Resolva a pergunta abaixo de forma clara e precisa.

        PERGUNTA: {query}

        INSTRUÇÕES:
        - Calcule corretamente e mostre o resultado final
        - Explique brevemente os passos principais
        - Use símbolos matemáticos quando necessário
        - Escreva em português brasileiro
        - Destaque a resposta final claramente

        RESPOSTA:"""

        payload = {
            "model": "llama3.2",
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9
            }
        }

        return payload

    async def process(self, query: str, conversation_id: str = None, user_id: str = None):
        """Process query and yield streaming responses"""
        start = time.time()
        full_response = ""

        yield {
            "type": "sources",
            "data": {
                "sources": ["Cálculos Matemáticos"],
                "processing": "resolvendo problema matemático"
            }
        }

        payload = self.build_llm_payload(query=query, stream=True)

        async for chunk in self.call_llm(payload):
            full_response += chunk
            yield {
                "type": "chunk",
                "data": {
                    "content": chunk,
                    "agent": "MathAgent"
                }
            }

        execution_time = time.time() - start

        log_agent_execution(
            logger=logger,
            agent_name="MathAgent",
            conversation_id=conversation_id or "unknown",
            user_id=user_id or "unknown",
            execution_time=execution_time,
            processed_content=f"Query: {query[:100]}... Response: {full_response[:300]}...",
            decision="Mathematical calculation processed"
        )
