from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from services.status_manager import status_events
from dependencies import inject_user_id

router = APIRouter(prefix="/status", tags=["v2/status"], dependencies=[Depends(inject_user_id)])


@router.get("/{thread_id}")
async def status_stream(
    thread_id: str,
):
    async def event_generator():
        async for message in status_events(thread_id):
            yield f"data: {message}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
