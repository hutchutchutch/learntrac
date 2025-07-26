# LearnTrac API Routers

from .analytics import router as analytics_router
from .voice import router as voice_router
from .chat import router as chat_router
from .learning import router as learning_router
from .vector_search import router as vector_search_router
from .llm import router as llm_router
from .tickets import router as tickets_router
from .evaluation import router as evaluation_router
from .trac import router as trac_router

__all__ = [
    "analytics_router",
    "voice_router",
    "chat_router",
    "learning_router",
    "vector_search_router",
    "llm_router",
    "tickets_router",
    "evaluation_router",
    "trac_router"
]