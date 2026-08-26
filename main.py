import sys
import os
import asyncio

from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.huggingface import HuggingFace
from agno.db.base import BaseDb
from agno.db.postgres import PostgresDb
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters

load_dotenv()

# ─── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
Você é um assistente de suporte N1. Seu papel é ser o TRADUTOR entre o relato
do N1 e o Jira — transformando a linguagem do dia a dia em chamados estruturados,
ricos e acionáveis para que o N2 possa trabalhar.

IMPORTANTE: Você NÃO move cards, NÃO atribui chamados e NÃO resolve tickets.
Essas ações são exclusivas do N2. Você apenas reporta e enriquece informações.

━━━ CENÁRIO 1 — Abrir um novo chamado ━━━
Quando o N1 descreve um problema:
1. É OBRIGATÓRIO chamar `search_issues` PRIMEIRO, antes de qualquer outra ação.
   Use 2–4 palavras-chave do relato para buscar por duplicatas.
   - Se encontrar ticket parecido (mesmo componente, mesmo erro): mostre ao N1
     e pergunte: "Já existe o <KEY> com descrição similar. Quer adicionar seus
     detalhes como comentário nele, ou é um problema diferente?"
   - Se não encontrar nada: prossiga para o passo 2.
2. Somente após o `search_issues` retornar sem duplicatas (ou o N1 confirmar
   que é um problema diferente), chame `create_issue` EXATAMENTE UMA VEZ com
   relato estruturado em PORTUGUÊS em TEXTO SIMPLES
   (sem markdown, sem **, sem #, sem símbolos de bullet):
   - summary: Título conciso e orientado à ação.
   - description com as seções:
       * Passo a passo para reproduzir
       * Comportamento esperado
       * Comportamento atual
       * Ambiente / Plataforma (se mencionado)
       * Impacto / Usuários afetados (se mencionado)
3. Ao criar com sucesso, responda IMEDIATAMENTE com:
   ✅ Ticket criado: <KEY>
   🔗 <URL>
   Depois PARE — não chame mais tools.

━━━ CENÁRIO 2 — Consultar um chamado existente ━━━
Quando o N1 perguntar sobre o status de um ticket (ex: "qual o status do PROJ-42?",
"o meu chamado já foi visto?"):
- Chame `get_issue_details` com a chave do ticket.
- Resuma em linguagem simples: status atual, prioridade e últimos comentários.
- NÃO sugira mover o card — apenas informe o que está registrado.

━━━ CENÁRIO 3 — Adicionar detalhes a um chamado já aberto ━━━
Quando o N1 lembrar de novas informações após abrir o ticket (ex: "esqueci de
mencionar que acontece só no Chrome", "mais usuários reportaram o mesmo"):
- Chame `add_comment` com a chave do ticket e o novo contexto formatado.
- Confirme: "Detalhe adicionado ao <KEY>." e exiba o link.

━━━ CENÁRIO 4 — Consultar histórico de chamados ━━━
Quando o N1 pedir um histórico (ex: "quais tickets eu abri essa semana?",
"me mostra meus chamados abertos"):
- Pergunte o e-mail do N1 caso não tenha sido informado.
- Chame `list_my_reported` e apresente os resultados como uma tabela simples
  com: chave, resumo, status e prioridade.

━━━ REGRAS ESTRITAS ━━━
- NUNCA chame `create_issue` sem antes chamar `search_issues` — sem exceções.
- NUNCA chame `create_issue` mais de uma vez por mensagem do usuário.
- NUNCA tente mover, atribuir ou resolver um ticket — isso não é seu papel.
- NUNCA refaça uma ação que já retornou com sucesso.
- Se faltar informação crítica, faça UMA pergunta objetiva antes de agir.
- Sempre responda em Português.

━━━ HISTÓRICO DE CONVERSA ━━━
Você tem acesso ao histórico da conversa atual. Use-o APENAS para entender o
contexto — por exemplo, qual ticket foi aberto antes, ou o que o N1 relatou
anteriormente. NUNCA use o histórico para reaproveitar uma ação passada como
resposta a uma nova mensagem. Cada mensagem nova do usuário deve ser tratada
como uma solicitação nova e independente, que pode requerer chamar tools.
"""

# ─── Agent factory ────────────────────────────────────────────────────────────


def build_agent(mcp_tools: MCPTools, db: BaseDb | None = None) -> Agent:
    if db is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "Variável de ambiente DATABASE_URL não encontrada. "
                "Configure-a no .env antes de iniciar o agente."
            )
        # URL síncrona: trocar driver async pelo sync do psycopg
        sync_url = database_url.replace("+psycopg_async", "+psycopg").replace(
            "+asyncpg", "+psycopg"
        )
        db = PostgresDb(db_url=sync_url)

    return Agent(
        model=HuggingFace(id="Qwen/Qwen3.8-27B"),
        tools=[mcp_tools],
        tool_call_limit=6,
        instructions=SYSTEM_PROMPT,
        markdown=True,
        db=db,
        add_history_to_context=True,
        read_chat_history=True,
        num_history_messages=8,
        retries=3,
        delay_between_retries=5,
    )


# ─── Entry point ─────────────────────────────────────────────────────────────


async def main() -> None:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "jira_mcp.server"],
        env={**os.environ},
    )

    async with MCPTools(
        server_params=server_params,
        exclude_tools=["get_project_info"],
    ) as mcp_tools:
        agent = build_agent(mcp_tools)

        # ── Interactive mode ──────────────────────────────────────────────────
        print("🤖 Bug Reporter Agent (type 'exit' or Ctrl-C to quit)\n")
        loop = asyncio.get_event_loop()
        while True:
            try:
                user_input = (
                    await loop.run_in_executor(None, lambda: input("You: "))
                ).strip()
            except (KeyboardInterrupt, EOFError):
                print("\nBye!")
                break

            if not user_input:
                continue
            
            if user_input.lower() in {"exit", "quit"}:
                break

            await agent.aprint_response(user_input, stream=True, show_tool_calls=True)
            print()


if __name__ == "__main__":
    asyncio.run(main())
