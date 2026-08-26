"""
Ferramentas MCP expostas ao agente.
Registradas via register_tools(mcp) para manter o servidor desacoplado das tools.

Cada tool atua como um adapter MCP fino: recebe os parâmetros do LLM,
delega a execução ao JiraService e trata eventuais erros retornando
mensagens padronizadas. A lógica de negócio e comunicação com o Jira SDK
reside exclusivamente em `jira_mcp.service`.

Tools:
  - get_project_info   : Retorna tipos de issue e componentes de um projeto.
  - search_issues      : Busca issues existentes via JQL (verificação de duplicatas).
  - create_issue       : Cria uma nova issue (Task) no projeto padrão.
  - get_issue_details  : Retorna detalhes completos (status, prioridade, comentários).
  - add_comment        : Adiciona um comentário com contexto a um ticket existente.
  - list_my_reported   : Lista tickets reportados por um dado endereço de e-mail.
"""

from fastmcp import FastMCP
from jira.exceptions import JIRAError

from jira_mcp.service import JiraService, UserNotFoundError
from jira_schemas.issue import (
    AddCommentResponse,
    AgentNote,
    IssueDetailsResponse,
    IssueItemResponse,
    PriorityEnum,
    ProjectInfoResponse,
    ReportedIssueItem,
)


def register_tools(mcp: FastMCP, service: JiraService | None = None) -> None:
    """
    Registra todas as ferramentas no servidor FastMCP fornecido.

    Args:
        mcp:     Instância do servidor FastMCP.
        service: Instância opcional de JiraService. Se não fornecida, uma nova
                 instância com configuração padrão (via variáveis de ambiente)
                 será criada. Útil para injeção de dependência em testes.
    """
    _service = service or JiraService()

    @mcp.tool(title="Get Project Info")
    def get_project_info(project_key: str = "") -> ProjectInfoResponse | dict:
        """
        Returns issue types and components for a Jira project.

        Args:
            project_key: The Jira project key (e.g. 'PROJ'). Defaults to the
                         value of the JIRA_PROJECT_KEY environment variable.
        """
        try:
            return _service.get_project_info(project_key or None)
        except JIRAError as e:
            return {"error": f"Jira API error [{e.status_code}]: {e.text}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    @mcp.tool(title="Search Issues")
    def search_issues(query: str, max_results: int = 5) -> list[IssueItemResponse] | list[dict]:
        """
        Searches for existing Jira issues to check for duplicates before opening
        a new ticket. Accepts either a plain-text query or a full JQL string.

        Args:
            query:       Plain-text search terms or a full JQL expression.
            max_results: Maximum number of results to return (default 5).
        """
        try:
            return _service.search_issues(query, max_results)
        except JIRAError as e:
            return [{"error": f"Jira API error [{e.status_code}]: {e.text}"}]
        except Exception as e:
            return [{"error": f"Unexpected error: {str(e)}"}]

    @mcp.tool(title="Create Jira Issue")
    def create_issue(
        summary: str,
        description: str,
        priority: PriorityEnum = PriorityEnum.MEDIUM,
    ) -> IssueItemResponse | dict:
        """
        Creates a new Jira issue (Task) in the default project.

        IMPORTANT: Call this tool EXACTLY ONCE per user message. Never retry if
        this tool returns successfully.

        Args:
            summary:     Concise, action-oriented title for the ticket.
            description: Structured bug report in plain text (no markdown).
            priority:    One of 'Lowest', 'Low', 'Medium', 'High', 'Highest'.
                         Defaults to 'Medium'.
        """
        try:
            return _service.create_issue(summary, description, priority)
        except JIRAError as e:
            return {"error": f"Jira API error [{e.status_code}]: {e.text}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    @mcp.tool(title="Get Issue Details")
    def get_issue_details(issue_key: str) -> IssueDetailsResponse | dict:
        """
        Returns full details of a Jira ticket so that N1 can check whether a
        similar issue already exists before opening a new one, or track the
        progress of a ticket they previously reported.

        Returns the last 3 comments to keep context concise.

        Args:
            issue_key: The Jira issue key (e.g. 'PROJ-42').
        """
        try:
            return _service.get_issue_details(issue_key)
        except JIRAError as e:
            return {"error": f"Jira API error [{e.status_code}]: {e.text}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    @mcp.tool(title="Add Comment")
    def add_comment(issue_key: str, comment: str) -> AddCommentResponse | dict:
        """
        Appends a comment to an existing Jira ticket.

        Use this when N1 has additional context to share after the ticket was
        created — for example, extra reproduction steps, affected users, or
        environment details they forgot to mention initially.

        Args:
            issue_key: The Jira issue key (e.g. 'PROJ-42').
            comment:   The comment text to append (plain text).
        """
        try:
            return _service.add_comment(issue_key, comment)
        except JIRAError as e:
            return {"error": f"Jira API error [{e.status_code}]: {e.text}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    @mcp.tool(title="List My Reported Issues")
    def list_my_reported(
        email: str, status: str = "", max_results: int = 10
    ) -> list[ReportedIssueItem | AgentNote | dict]:
        """
        Lists Jira tickets reported by a given e-mail address.
        Issues with status 'Concluído' are NEVER included in the result list.

        If any 'Concluído' tickets exist, a leading entry with key "_agent_note" will
        appear in the results. When you see it, inform the user naturally that those
        requests were already resolved — do NOT list them individually.

        Args:
            email:       The reporter's e-mail address (e.g. user@example.com).
            status:      Optional status filter, e.g. 'Open', 'In Progress'.
                         Leave empty to return all non-'Concluído' issues.
            max_results: Maximum number of issues to return (default 10).
        """
        try:
            return _service.list_my_reported(email, status, max_results)
        except UserNotFoundError as e:
            return [{"error": str(e)}]
        except JIRAError as e:
            return [{"error": f"Jira API error [{e.status_code}]: {e.text}"}]
        except Exception as e:
            return [{"error": f"Unexpected error: {str(e)}"}]
