from datetime import datetime
import json
import logging
import os
import time
import traceback
from contextlib import asynccontextmanager
from typing import List, Optional, AsyncGenerator

import redis
from fastapi import FastAPI, HTTPException, Cookie, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from infra.cache import redis_client
from infra.logs import setup_logging, log_agent_execution
from src.conversation import ConversationManager
from src.rag.retriever import RAGRetriever
from src.router import RouterAgent, conversation_session

logger = setup_logging(log_level=logging.INFO, redis_client=redis_client)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.rag.builder import build_rag_documents
    await build_rag_documents()
    yield


app = FastAPI(title="Chat Infinite API", version="0.0.1", lifespan=lifespan)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:8080,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None


class AgentWorkflowStep(BaseModel):
    agent: str
    decision: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    source_agent_response: str
    agent_workflow: List[AgentWorkflowStep]


conversation_manager = ConversationManager(redis_client)


@app.post("/chat")
async def chat(
        request: ChatMessage,
        response: Response,
        user_id: Optional[str] = Cookie(None),
        conversation_id: Optional[str] = Cookie(None)
):
    async def generate_stream() -> AsyncGenerator[str, None]:
        request_start_time = time.time()
        agent = None
        current_user_id = None
        current_conversation_id = None

        try:

            conversation_manager = ConversationManager(redis_client)

            effective_user_id = user_id or request.user_id
            effective_conversation_id = conversation_id or request.conversation_id

            async with conversation_session(conversation_manager, effective_user_id) as session_user_id:
                current_user_id = session_user_id

                if not user_id:
                    response.set_cookie(
                        "user_id",
                        current_user_id,
                        max_age=30 * 24 * 60 * 60,
                        httponly=True,
                        secure=False,
                        samesite="lax"
                    )

                if not effective_conversation_id or not conversation_manager.get_conversation_info(
                        effective_conversation_id):
                    current_conversation_id = conversation_manager.create_conversation(current_user_id)
                    response.set_cookie(
                        "conversation_id",
                        current_conversation_id,
                        max_age=30 * 24 * 60 * 60,
                        httponly=True,
                        secure=False,
                        samesite="lax"
                    )
                else:
                    current_conversation_id = effective_conversation_id

                conversation_manager.add_message(
                    current_conversation_id,
                    request.message,
                    "user"
                )

                rag_retriever = RAGRetriever()
                router = RouterAgent(rag_retriever, conversation_manager)

                agent_type = router.classify(
                    request.message,
                    current_conversation_id,
                    current_user_id
                )

                agent = agent_type.value.capitalize() + "Agent"

                agent_selection_data = {
                    "type": "agent_selection",
                    "data": {
                        "agent": agent,
                        "decision": f"Routing to {agent_type.value} agent",
                        "conversation_id": current_conversation_id,
                        "user_id": current_user_id,
                    }
                }
                yield f"data: {json.dumps(agent_selection_data)}\n\n"

                selected_agent = router.agents[agent_type]
                assistant_response = ""

                async for chunk_data in selected_agent.process(
                    request.message,
                    conversation_id=current_conversation_id,
                    user_id=current_user_id,
                ):
                    if chunk_data.get("type") == "chunk":
                        assistant_response += chunk_data.get("data", {}).get("content", "")
                    yield f"data: {json.dumps(chunk_data)}\n\n"

                if assistant_response.strip():
                    conversation_manager.add_message(
                        current_conversation_id,
                        assistant_response,
                        "assistant",
                        agent=agent,
                        metadata={
                            "agent_type": agent_type.value,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

                completion_data = {
                    "type": "complete",
                    "data": {
                        "conversation_id": current_conversation_id,
                        "user_id": current_user_id,
                        "message_count": conversation_manager.get_conversation_info(current_conversation_id).get(
                            "message_count", 0)
                    }
                }
                yield f"data: {json.dumps(completion_data)}\n\n"

                total_execution_time = time.time() - request_start_time
                log_agent_execution(
                    logger=logger,
                    agent_name=agent,
                    conversation_id=current_conversation_id or "unknown",
                    user_id=current_user_id or "unknown",
                    execution_time=total_execution_time,
                    processed_content=f"Message processed successfully: {request.message[:100]}...",
                    decision=f"Chat completed using {agent} in {total_execution_time:.2f}s"
                )

        except redis.ConnectionError:
            error_execution_time = time.time() - request_start_time
            error_data = {
                "type": "error",
                "data": {"message": "Sistema de conversação temporariamente indisponível"}
            }
            yield f"data: {json.dumps(error_data)}\n\n"

            log_agent_execution(
                logger=logger,
                agent_name=agent,
                conversation_id=current_conversation_id or "unknown",
                user_id=current_user_id or "unknown",
                execution_time=error_execution_time,
                processed_content=f"Redis connection failed while processing: {request.message[:100]}...",
                decision="Failed due to Redis connection error",
                level="ERROR"
            )

        except Exception as e:
            traceback.print_exc()
            error_execution_time = time.time() - request_start_time
            error_data = {
                "type": "error",
                "data": {"message": "Erro ao processar mensagem"}
            }
            yield f"data: {json.dumps(error_data)}\n\n"

            log_agent_execution(
                logger=logger,
                agent_name=agent,
                conversation_id=current_conversation_id or "unknown",
                user_id=current_user_id or "unknown",
                execution_time=error_execution_time,
                processed_content=f"Error processing message: {request.message[:100]}...",
                decision=f"Failed with error: {str(e)[:200]}...",
                level="ERROR"
            )

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": os.getenv("ACCESS_CONTROL_ALLOW_ORIGIN", "http://localhost:5173"),
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Credentials": "true"
        }
    )


@app.get("/conversations")
async def get_user_conversations(
        response: Response,
        request: Request
):
    """Get all conversations for current user"""
    start_time = time.time()
    user_id = None

    try:
        user_id = request.cookies.get("user_id")

        if not user_id:
            user_id = conversation_manager.get_or_create_user_session()
            response.set_cookie(
                "user_id",
                user_id,
                max_age=30 * 24 * 60 * 60,
                httponly=True,
                secure=False,
                samesite="lax"
            )

        conversations = conversation_manager.get_user_conversations(user_id)

        execution_time = time.time() - start_time
        log_agent_execution(
            logger=logger,
            agent_name="ConversationsEndpoint",
            conversation_id="list_all",
            user_id=user_id,
            execution_time=execution_time,
            processed_content=f"Retrieved {len(conversations)} conversations",
            decision="Successfully retrieved user conversations"
        )

        return {"conversations": conversations}
    except Exception as e:
        execution_time = time.time() - start_time
        log_agent_execution(
            logger=logger,
            agent_name="ConversationsEndpoint",
            conversation_id="list_all",
            user_id=user_id or "unknown",
            execution_time=execution_time,
            processed_content="Failed to retrieve conversations",
            decision=f"Failed with error: {str(e)}",
            level="ERROR"
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations/{conversation_id}/history")
async def get_conversation_history(
        conversation_id: str,
        response: Response,
        user_id: Optional[str] = Cookie(None),
        limit: int = 50
):
    """Get conversation message history"""
    start_time = time.time()

    try:

        response.headers["Access-Control-Allow-Origin"] = os.getenv("ACCESS_CONTROL_ALLOW_ORIGIN",
                                                                    "http://localhost:5173")
        response.headers["Access-Control-Allow-Credentials"] = "true"

        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        conv_info = conversation_manager.get_conversation_info(conversation_id)
        if not conv_info or conv_info.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages = conversation_manager.get_conversation_history(conversation_id, limit)

        execution_time = time.time() - start_time
        log_agent_execution(
            logger=logger,
            agent_name="ConversationHistoryEndpoint",
            conversation_id=conversation_id,
            user_id=user_id,
            execution_time=execution_time,
            processed_content=f"Retrieved {len(messages)} messages from conversation",
            decision="Successfully retrieved conversation history"
        )

        return {
            "conversation_id": conversation_id,
            "messages": [msg.model_dump() for msg in messages],
            "conversation_info": conv_info
        }
    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        log_agent_execution(
            logger=logger,
            agent_name="ConversationHistoryEndpoint",
            conversation_id=conversation_id,
            user_id=user_id or "unknown",
            execution_time=execution_time,
            processed_content="Failed to retrieve conversation history",
            decision=f"Failed with error: {str(e)}",
            level="ERROR"
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/conversations/new")
async def create_new_conversation(
        response: Response,
        user_id: Optional[str] = Cookie(None),
        title: Optional[str] = None
):
    """Create a new conversation"""
    start_time = time.time()
    conversation_id = None

    try:

        response.headers["Access-Control-Allow-Origin"] = os.getenv("ACCESS_CONTROL_ALLOW_ORIGIN",
                                                                    "http://localhost:5173")
        response.headers["Access-Control-Allow-Credentials"] = "true"

        if not user_id:
            user_id = conversation_manager.get_or_create_user_session()
            response.set_cookie(
                "user_id",
                user_id,
                max_age=30 * 24 * 60 * 60,
                httponly=True,
                secure=False,
                samesite="lax"
            )

        conversation_id = conversation_manager.create_conversation(user_id, title)
        response.set_cookie("conversation_id", conversation_id, max_age=30 * 24 * 60 * 60)

        execution_time = time.time() - start_time
        log_agent_execution(
            logger=logger,
            agent_name="CreateConversationEndpoint",
            conversation_id=conversation_id,
            user_id=user_id,
            execution_time=execution_time,
            processed_content=f"Created new conversation with title: {title or 'Untitled'}",
            decision="Successfully created new conversation"
        )

        return {
            "conversation_id": conversation_id,
            "message": "New conversation created"
        }
    except Exception as e:
        execution_time = time.time() - start_time
        log_agent_execution(
            logger=logger,
            agent_name="CreateConversationEndpoint",
            conversation_id=conversation_id or "unknown",
            user_id=user_id or "unknown",
            execution_time=execution_time,
            processed_content="Failed to create new conversation",
            decision=f"Failed with error: {str(e)}",
            level="ERROR"
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(
        conversation_id: str,
        response: Response,
        user_id: Optional[str] = Cookie(None)
):
    """Delete a conversation"""
    start_time = time.time()

    try:

        response.headers["Access-Control-Allow-Origin"] = os.getenv("ACCESS_CONTROL_ALLOW_ORIGIN",
                                                                    "http://localhost:5173")
        response.headers["Access-Control-Allow-Credentials"] = "true"

        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        success = conversation_manager.delete_conversation(conversation_id, user_id)
        execution_time = time.time() - start_time

        if success:
            log_agent_execution(
                logger=logger,
                agent_name="DeleteConversationEndpoint",
                conversation_id=conversation_id,
                user_id=user_id,
                execution_time=execution_time,
                processed_content="Conversation deleted successfully",
                decision="Successfully deleted conversation"
            )
            return {"message": "Conversation deleted successfully"}
        else:
            log_agent_execution(
                logger=logger,
                agent_name="DeleteConversationEndpoint",
                conversation_id=conversation_id,
                user_id=user_id,
                execution_time=execution_time,
                processed_content="Conversation not found for deletion",
                decision="Conversation not found",
                level="DEBUG"
            )
            raise HTTPException(status_code=404, detail="Conversation not found")
    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        log_agent_execution(
            logger=logger,
            agent_name="DeleteConversationEndpoint",
            conversation_id=conversation_id,
            user_id=user_id or "unknown",
            execution_time=execution_time,
            processed_content="Failed to delete conversation",
            decision=f"Failed with error: {str(e)}",
            level="ERROR"
        )
        raise HTTPException(status_code=500, detail=str(e))


class TitleUpdateRequest(BaseModel):
    title: str


@app.put("/conversations/{conversation_id}/title")
async def update_conversation_title(
        conversation_id: str,
        request: TitleUpdateRequest,
        response: Response,
        user_id: Optional[str] = Cookie(None)
):
    """Update conversation title"""
    start_time = time.time()

    try:

        response.headers["Access-Control-Allow-Origin"] = os.getenv("ACCESS_CONTROL_ALLOW_ORIGIN",
                                                                    "http://localhost:5173")
        response.headers["Access-Control-Allow-Credentials"] = "true"

        if not user_id:
            raise HTTPException(status_code=401, detail="User authentication required")

        conv_info = conversation_manager.get_conversation_info(conversation_id)
        if not conv_info or conv_info.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Conversation not found")

        success = conversation_manager.update_conversation_title(conversation_id, request.title)
        execution_time = time.time() - start_time

        if success:
            log_agent_execution(
                logger=logger,
                agent_name="UpdateTitleEndpoint",
                conversation_id=conversation_id,
                user_id=user_id,
                execution_time=execution_time,
                processed_content=f"Updated title to: {request.title}",
                decision="Successfully updated conversation title"
            )
            return {"message": "Title updated successfully"}
        else:
            log_agent_execution(
                logger=logger,
                agent_name="UpdateTitleEndpoint",
                conversation_id=conversation_id,
                user_id=user_id,
                execution_time=execution_time,
                processed_content="Failed to update conversation title",
                decision="Failed to update title in database",
                level="ERROR"
            )
            raise HTTPException(status_code=500, detail="Failed to update title")
    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        log_agent_execution(
            logger=logger,
            agent_name="UpdateTitleEndpoint",
            conversation_id=conversation_id,
            user_id=user_id or "unknown",
            execution_time=execution_time,
            processed_content="Failed to update conversation title",
            decision=f"Failed with error: {str(e)}",
            level="ERROR"
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs")
async def get_logs(
        limit: int = 100,
        level: Optional[str] = None,
        agent: Optional[str] = None
):
    """Get application logs from Redis storage"""
    start_time = time.time()

    try:
        # Get logs from Redis
        logs = redis_client.lrange("app_logs", 0, limit - 1)
        parsed_logs = []

        for log_entry in logs:
            try:
                log_data = json.loads(log_entry.decode('utf-8'))

                # Filter by level if specified
                if level and log_data.get("level") != level.upper():
                    continue

                # Filter by agent if specified
                if agent and log_data.get("agent") != agent:
                    continue

                parsed_logs.append(log_data)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

        execution_time = time.time() - start_time
        log_agent_execution(
            logger=logger,
            agent_name="LogsEndpoint",
            conversation_id="logs_request",
            user_id="admin",
            execution_time=execution_time,
            processed_content=f"Retrieved {len(parsed_logs)} log entries with filters: level={level}, agent={agent}",
            decision=f"Successfully retrieved logs from Redis"
        )

        return {
            "logs": parsed_logs,
            "total_retrieved": len(parsed_logs),
            "filters_applied": {
                "level": level,
                "agent": agent,
                "limit": limit
            }
        }
    except Exception as e:
        execution_time = time.time() - start_time
        log_agent_execution(
            logger=logger,
            agent_name="LogsEndpoint",
            conversation_id="logs_request",
            user_id="admin",
            execution_time=execution_time,
            processed_content="Failed to retrieve logs from Redis",
            decision=f"Failed with error: {str(e)}",
            level="ERROR"
        )
        raise HTTPException(status_code=500, detail=str(e))
