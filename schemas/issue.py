from enum import Enum

from pydantic import BaseModel


# ─── Enums ────────────────────────────────────────────────────────────────────


class PriorityEnum(str, Enum):
    LOWEST = "Lowest"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    HIGHEST = "Highest"


# ─── Respostas: get_project_info ──────────────────────────────────────────────


class ProjectInfoResponse(BaseModel):
    project_key: str
    project_name: str
    issue_types: list[str]
    components: list[str]


# ─── Respostas: search_issues / create_issue / list_my_reported ───────────────


class IssueItemResponse(BaseModel):
    key: str
    summary: str
    status: str
    url: str


# ─── Respostas: get_issue_details ─────────────────────────────────────────────


class CommentItem(BaseModel):
    author: str
    body: str
    created: str


class IssueDetailsResponse(BaseModel):
    key: str
    summary: str
    status: str
    priority: str
    assignee: str
    created: str
    updated: str
    recent_comments: list[CommentItem]
    url: str


# ─── Respostas: add_comment ───────────────────────────────────────────────────


class AddCommentResponse(BaseModel):
    issue_key: str
    comment_id: str
    author: str
    created: str
    url: str
    message: str


# ─── Resposta: list_my_reported (inclui nota interna do agente) ───────────────


class ReportedIssueItem(BaseModel):
    key: str
    summary: str
    status: str
    created: str
    url: str


class AgentNote(BaseModel):
    _agent_note: str
