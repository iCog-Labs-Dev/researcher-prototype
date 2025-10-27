from fastapi import APIRouter

from .user import router as user_router
from .auth import router as auth_router
from .meta import router as meta_router
from .chat import router as chat_router
from .graph import router as graph_router
from .notification import router as notification_router
from .status import router as status_router
from .topic import router as topic_router
from .research import router as research_router
from api.v2.admin import router as admin_router

router = APIRouter(prefix="/v2")

router.include_router(admin_router)
router.include_router(user_router)
router.include_router(auth_router)
router.include_router(meta_router)
router.include_router(chat_router)
router.include_router(graph_router)
router.include_router(notification_router)
router.include_router(status_router)
router.include_router(topic_router)
router.include_router(research_router)
