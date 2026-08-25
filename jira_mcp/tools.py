"""
Ferramentas MCP expostas ao agente.
Registradas via register_tools(mcp) para manter o servidor desacoplado das tools.

Tools:
  - get_project_info   : Retorna tipos de issue e componentes de um projeto.
  - search_issues      : Busca issues existentes via JQL (verificação de duplicatas).
  - create_issue       : Cria uma nova issue (Task) no projeto padrão.
  - get_issue_details  : Retorna detalhes completos (status, prioridade, comentários).
  - add_comment        : Adiciona um comentário com contexto a um ticket existente.
  - set_priority       : Atualiza a prioridade de um ticket existente.
  - list_my_reported   : Lista tickets reportados por um dado endereço de e-mail.
"""

from fastmcp import FastMCP
from jira.exceptions import JIRAError

from jira_mcp.client import get_client, get_default_project, issue_url


def register_tools(mcp: FastMCP) -> None:
    """Registra todas as ferramentas no servidor FastMCP fornecido."""

    @mcp.tool(title="Get Project Info")
    def get_project_info(project_key: str = "") -> dict:
        """
        Returns issue types and components for a Jira project.

        Args:
            project_key: The Jira project key (e.g. 'PROJ'). Defaults to the
                         value of the JIRA_PROJECT_KEY environment variable.
        """
        key = project_key or get_default_project()
        try:
            jira = get_client()
            project = jira.project(key)
            issue_types = [it.name for it in jira.issue_types_for_project(key)]
            components = [c.name for c in jira.project_components(key)]
            return {
                "project_key": project.key,
                "project_name": project.name,
                "issue_types": issue_types,
                "components": components,
            }
        except JIRAError as e:
            return {"error": f"Jira API error [{e.status_code}]: {e.text}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    @mcp.tool(title="Search Issues")
    def search_issues(query: str, max_results: int = 5) -> list[dict]:
        """
        Searches for existing Jira issues to check for duplicates before opening
        a new ticket. Accepts either a plain-text query or a full JQL string.

        Args:
            query:       Plain-text search terms or a full JQL expression.
            max_results: Maximum number of results to return (default 5).
        """
        key = get_default_project()
        try:
            jira = get_client()
            if "=" not in query and "ORDER BY" not in query.upper():
                jql = f'project = "{key}" AND text ~ "{query}" ORDER BY created DESC'
            else:
                jql = query

            issues = jira.search_issues(jql, maxResults=max_results)
            return [
                {
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "status": issue.fields.status.name,
                    "url": issue_url(issue.key),
                }
                for issue in issues
            ]
        except JIRAError as e:
            return [{"error": f"Jira API error [{e.status_code}]: {e.text}"}]
        except Exception as e:
            return [{"error": f"Unexpected error: {str(e)}"}]

    @mcp.tool(title="Create Jira Issue")
    def create_issue(
        summary: str,
        description: str,
        priority: str = "Medium",
    ) -> dict:
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
        key = get_default_project()
        try:
            jira = get_client()
            issue_dict = {
                "project": {"key": key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": "Task"},
                "priority": {"name": priority},
            }
            new_issue = jira.create_issue(fields=issue_dict)
            return {
                "key": new_issue.key,
                "summary": new_issue.fields.summary,
                "url": issue_url(new_issue.key),
            }
        except JIRAError as e:
            return {"error": f"Jira API error [{e.status_code}]: {e.text}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    @mcp.tool(title="Get Issue Details")
    def get_issue_details(issue_key: str) -> dict:
        """
        Returns full details of a Jira ticket so that N1 can check whether a
        similar issue already exists before opening a new one, or track the
        progress of a ticket they previously reported.

        Returns the last 3 comments to keep context concise.

        Args:
            issue_key: The Jira issue key (e.g. 'PROJ-42').
        """
        try:
            jira = get_client()
            issue = jira.issue(
                issue_key,
                fields="summary,status,priority,assignee,comment,created,updated",
            )
            fields = issue.fields

            comments_raw = getattr(fields.comment, "comments", [])
            recent_comments = [
                {
                    "author": c.author.displayName,
                    "body": c.body[:300] + ("..." if len(c.body) > 300 else ""),
                    "created": c.created[:10],
                }
                for c in comments_raw[-3:]
            ]

            return {
                "key": issue.key,
                "summary": fields.summary,
                "status": fields.status.name,
                "priority": fields.priority.name if fields.priority else "Não definida",
                "assignee": fields.assignee.displayName if fields.assignee else "Não atribuído",
                "created": fields.created[:10],
                "updated": fields.updated[:10],
                "recent_comments": recent_comments,
                "url": issue_url(issue.key),
            }
        except JIRAError as e:
            return {"error": f"Jira API error [{e.status_code}]: {e.text}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    @mcp.tool(title="Add Comment")
    def add_comment(issue_key: str, comment: str) -> dict:
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
            jira = get_client()
            new_comment = jira.add_comment(issue_key, comment)
            return {
                "issue_key": issue_key,
                "comment_id": new_comment.id,
                "author": new_comment.author.displayName,
                "created": new_comment.created[:10],
                "url": issue_url(issue_key),
                "message": f"Comentário adicionado com sucesso ao ticket {issue_key}.",
            }
        except JIRAError as e:
            return {"error": f"Jira API error [{e.status_code}]: {e.text}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    @mcp.tool(title="List My Reported Issues")
    def list_my_reported(email: str, status: str = "", max_results: int = 10) -> list[dict]:
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
        key = get_default_project()
        try:
            jira = get_client()

            users = jira.search_users(query=email)
            if not users:
                return [{"error": f"No Jira user found for e-mail: {email}"}]

            account_id = users[0].accountId

            base = f'project = "{key}" AND reporter = "{account_id}" AND status != "Concluído"'
            if status:
                base += f' AND status = "{status}"'
            jql = base + " ORDER BY created DESC"

            issues = jira.search_issues(jql, maxResults=max_results)

            completed_jql = (
                f'project = "{key}" AND reporter = "{account_id}" AND status = "Concluído"'
            )
            completed_issues = jira.search_issues(completed_jql, maxResults=1)

            result = []
            if completed_issues:
                result.append(
                    {
                        "_agent_note": (
                            "Existem chamados reportados por este usuário com status "
                            "'Concluído'. Informe ao usuário que essas ações já foram "
                            "realizadas, sem listá-las individualmente."
                        )
                    }
                )

            result.extend(
                [
                    {
                        "key": issue.key,
                        "summary": issue.fields.summary,
                        "status": issue.fields.status.name,
                        "created": issue.fields.created[:10],
                        "url": issue_url(issue.key),
                    }
                    for issue in issues
                ]
            )
            return result
        except JIRAError as e:
            return [{"error": f"Jira API error [{e.status_code}]: {e.text}"}]
        except Exception as e:
            return [{"error": f"Unexpected error: {str(e)}"}]
