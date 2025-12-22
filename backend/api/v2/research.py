from uuid import UUID
from typing import Optional, Annotated
from fastapi import APIRouter, Request, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from services.logging_config import get_logger
from dependencies import inject_user_id
from schemas.research import (
    BookmarkUpdateInOut,
    ResearchFindingsOut,
)
from services.research import ResearchService

router = APIRouter(prefix="/research", tags=["v2/research"], dependencies=[Depends(inject_user_id)])

logger = get_logger(__name__)


# need attention: there was a user_id parameter. is it correct?
@router.get("/findings", response_model=ResearchFindingsOut)
async def get_research_findings(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    topic_id: Optional[UUID] = Query(None, description="Filter by topic ID"),
    unread_only: bool = Query(False, description="Only return unread findings"),
) -> ResearchFindingsOut:
    user_id = str(request.state.user_id)

    service = ResearchService()
    findings = await service.get_findings(session, user_id, topic_id, unread_only)

    return ResearchFindingsOut(
        total_findings=len(findings),
        findings=findings
    )


@router.post("/findings/{finding_id}/mark_read")
async def mark_research_finding_read(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    finding_id: UUID,
):
    user_id = str(request.state.user_id)

    service = ResearchService()
    await service.mark_finding_as_read(session, user_id, finding_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/findings/{finding_id}/bookmark", response_model=BookmarkUpdateInOut)
async def bookmark_research_finding(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    finding_id: UUID,
    body: BookmarkUpdateInOut,
) -> BookmarkUpdateInOut:
    user_id = str(request.state.user_id)

    service = ResearchService()
    result = await service.mark_finding_bookmarked(session, user_id, finding_id, body.bookmarked)

    return BookmarkUpdateInOut(bookmarked=result)


@router.delete("/findings/{finding_id}")
async def delete_research_finding(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    finding_id: UUID,
):
    user_id = str(request.state.user_id)

    service = ResearchService()
    await service.delete_research_finding(session, user_id, finding_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/findings/topic/{topic_id}")
async def delete_all_topic_findings(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    topic_id: UUID,
):
    user_id = str(request.state.user_id)

    service = ResearchService()
    await service.delete_all_topic_findings(session, user_id, topic_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/findings/{finding_id}/integrate", deprecated=True, description="Deprecated: Zep integration disabled")
async def integrate_research_finding():
    return Response(status_code=status.HTTP_204_NO_CONTENT)
