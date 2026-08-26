from __future__ import annotations

from jira import JIRA
from jira.exceptions import JIRAError

from jira_mcp.client import get_client, get_default_project, issue_url
from schemas.issue import (
    AddCommentResponse,
    AgentNote,
    CommentItem,
    IssueDetailsResponse,
    IssueItemResponse,
    PriorityEnum,
    ProjectInfoResponse,
    ReportedIssueItem,
)


class JiraServiceError(Exception):
    pass


class UserNotFoundError(JiraServiceError):
    pass


class JiraService:
    def __init__(
        self,
        client: JIRA | None = None,
        default_project: str | None = None,
    ) -> None:
        self._client = client
        self._default_project = default_project

    @property
    def client(self) -> JIRA:
        if self._client is None:
            self._client = get_client()
        return self._client

    @property
    def default_project(self) -> str:
        return self._default_project or get_default_project()

    def get_project_info(self, project_key: str | None = None) -> ProjectInfoResponse:
        key = project_key or self.default_project
        project = self.client.project(key)
        issue_types = [it.name for it in self.client.issue_types_for_project(key)]
        components = [c.name for c in self.client.project_components(key)]
        return ProjectInfoResponse(
            project_key=project.key,
            project_name=project.name,
            issue_types=issue_types,
            components=components,
        )

    def search_issues(
        self, query: str, max_results: int = 5
    ) -> list[IssueItemResponse]:
        if "=" not in query and "ORDER BY" not in query.upper():
            jql = (
                f'project = "{self.default_project}" AND text ~ "{query}"'
                " ORDER BY created DESC"
            )
        else:
            jql = query

        issues = self.client.search_issues(jql, maxResults=max_results)
        return [
            IssueItemResponse(
                key=issue.key,
                summary=issue.fields.summary,
                status=issue.fields.status.name,
                url=issue_url(issue.key),
            )
            for issue in issues
        ]

    def create_issue(
        self,
        summary: str,
        description: str,
        priority: PriorityEnum = PriorityEnum.MEDIUM,
    ) -> IssueItemResponse:
        issue_dict = {
            "project": {"key": self.default_project},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Task"},
            "priority": {"name": priority.value},
        }
        new_issue = self.client.create_issue(fields=issue_dict)
        return IssueItemResponse(
            key=new_issue.key,
            summary=new_issue.fields.summary,
            status=new_issue.fields.status.name,
            url=issue_url(new_issue.key),
        )

    def get_issue_details(self, issue_key: str) -> IssueDetailsResponse:
        issue = self.client.issue(
            issue_key,
            fields="summary,status,priority,assignee,comment,created,updated",
        )
        fields = issue.fields

        comments_raw = getattr(fields.comment, "comments", [])
        recent_comments = [
            CommentItem(
                author=c.author.displayName,
                body=c.body[:300] + ("..." if len(c.body) > 300 else ""),
                created=c.created[:10],
            )
            for c in comments_raw[-3:]
        ]

        return IssueDetailsResponse(
            key=issue.key,
            summary=fields.summary,
            status=fields.status.name,
            priority=fields.priority.name if fields.priority else "Não definida",
            assignee=(
                fields.assignee.displayName if fields.assignee else "Não atribuído"
            ),
            created=fields.created[:10],
            updated=fields.updated[:10],
            recent_comments=recent_comments,
            url=issue_url(issue.key),
        )

    def add_comment(self, issue_key: str, comment: str) -> AddCommentResponse:
        new_comment = self.client.add_comment(issue_key, comment)
        return AddCommentResponse(
            issue_key=issue_key,
            comment_id=new_comment.id,
            author=new_comment.author.displayName,
            created=new_comment.created[:10],
            url=issue_url(issue_key),
            message=f"Comentário adicionado com sucesso ao ticket {issue_key}.",
        )

    def list_my_reported(
        self,
        email: str,
        status: str = "",
        max_results: int = 10,
    ) -> list[ReportedIssueItem | AgentNote]:
        users = self.client.search_users(query=email)
        if not users:
            raise UserNotFoundError(f"No Jira user found for e-mail: {email}")

        account_id = users[0].accountId
        key = self.default_project

        base_jql = (
            f'project = "{key}" AND reporter = "{account_id}"'
            ' AND status != "Concluído"'
        )
        if status:
            base_jql += f' AND status = "{status}"'
        jql = base_jql + " ORDER BY created DESC"

        issues = self.client.search_issues(jql, maxResults=max_results)

        completed_jql = (
            f'project = "{key}" AND reporter = "{account_id}"'
            ' AND status = "Concluído"'
        )
        completed_issues = self.client.search_issues(completed_jql, maxResults=1)

        result: list = []

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
                ReportedIssueItem(
                    key=issue.key,
                    summary=issue.fields.summary,
                    status=issue.fields.status.name,
                    created=issue.fields.created[:10],
                    url=issue_url(issue.key),
                )
                for issue in issues
            ]
        )
        return result
