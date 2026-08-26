import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from agno.agent import Agent

from api.dependencies import get_agent
from api.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Enviar mensagem ao agente",
    description=(
        "Recebe a mensagem do usuário N1 e o session_id, "
        "executa o agente (com histórico isolado por sessão no PostgreSQL) "
        "e retorna a resposta em texto."
    ),
)
async def chat(
    body: ChatRequest,
    agent: Agent = Depends(get_agent),
) -> ChatResponse:
    session_id = body.session_id or str(uuid.uuid4())
    try:
        run_response = await agent.arun(body.message, session_id=session_id)
        content = run_response.content if run_response.content else ""
        return ChatResponse(session_id=session_id, response=content)
    except Exception as exc:
        logger.exception("Erro ao executar o agente para session_id=%s", session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do agente: {exc}",
        ) from exc


@router.get(
    "/health",
    summary="Healthcheck",
    description="Retorna 200 OK quando a API e o agente estão prontos.",
)
async def health() -> dict:
    return {"status": "ok"}
