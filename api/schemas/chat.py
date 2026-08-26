from pydantic import BaseModel, Field


class ChatRequest(BaseModel):

    message: str = Field(..., description="Mensagem do usuário N1 em linguagem natural.")
    session_id: str = Field(
        default=None,
        description=(
            "UUID de sessão gerado pelo cliente. "
            "Isola o histórico de conversa no PostgreSQL por session_id."
        ),
    )


class ChatResponse(BaseModel):
    session_id: str = Field(..., description="Mesmo session_id enviado na requisição.")
    response: str = Field(..., description="Resposta do agente em texto (pode conter Markdown).")
