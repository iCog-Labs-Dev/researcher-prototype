from fastapi import APIRouter, Depends

from dependencies import inject_admin_id
from .user import router as user_router
from .flow import router as flow_router
from .prompt import router as prompt_router

router = APIRouter(prefix="/admin", tags=["v2/admin"], dependencies=[Depends(inject_admin_id)])

router.include_router(user_router)
router.include_router(flow_router)
router.include_router(prompt_router)
