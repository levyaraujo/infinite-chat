import logging
import sys
import json
import redis
from datetime import datetime, timezone
from logging import Logger
from typing import Optional

class RedisLogHandler(logging.Handler):
    """Custom handler that stores logs in Redis"""
    
    def __init__(self, redis_client: redis.Redis, log_key: str = "app_logs"):
        super().__init__()
        self.redis_client = redis_client
        self.log_key = log_key
    
    def emit(self, record):
        try:
            log_entry = self.format(record)
            self.redis_client.lpush(self.log_key, log_entry)
            self.redis_client.ltrim(self.log_key, 0, 9999)
        except Exception:
            pass

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
        }

        # Required fields from observability requirements
        for field in ["agent", "conversation_id", "user_id", "execution_time", "decision", "processed_content"]:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)

        if record.getMessage():
            log_entry["message"] = record.getMessage()

        return json.dumps(log_entry)

def setup_logging(log_level: int | str = logging.INFO, redis_client: Optional[redis.Redis] = None) -> Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    logger.handlers.clear()

    # Console handler for development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    formatter = JSONFormatter()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if redis_client:
        redis_handler = RedisLogHandler(redis_client)
        redis_handler.setLevel(log_level)
        redis_handler.setFormatter(formatter)
        logger.addHandler(redis_handler)

    return logger

def log_agent_execution(logger: Logger, agent_name: str, conversation_id: str, user_id: str, 
                       execution_time: float, decision: Optional[str] = None, 
                       processed_content: Optional[str] = None, level: str = "INFO"):
    """Helper function to log agent execution with all required fields"""
    log_record = logging.LogRecord(
        name=logger.name,
        level=getattr(logging, level),
        pathname="",
        lineno=0,
        msg="Agent execution completed",
        args=(),
        exc_info=None
    )
    
    log_record.agent = agent_name
    log_record.conversation_id = conversation_id
    log_record.user_id = user_id
    log_record.execution_time = execution_time
    
    if decision:
        log_record.decision = decision
    if processed_content:
        log_record.processed_content = processed_content[:500] + "..." if len(processed_content) > 500 else processed_content
    
    logger.handle(log_record)