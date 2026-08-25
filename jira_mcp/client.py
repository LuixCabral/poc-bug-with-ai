import os

from jira import JIRA

_jira_client: JIRA | None = None


def get_client() -> JIRA:
    """Retorna o cliente Jira autenticado (singleton lazy)."""
    global _jira_client
    if _jira_client is None:
        _jira_client = JIRA(
            server=os.environ["JIRA_URL"],
            basic_auth=(os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"]),
        )
    return _jira_client


def get_default_project() -> str:
    """Retorna a chave do projeto padrão definida no .env."""
    return os.environ["JIRA_PROJECT_KEY"]


def issue_url(issue_key: str) -> str:
    """Retorna a URL de browser para uma issue do Jira."""
    return f"{os.environ['JIRA_URL']}/browse/{issue_key}"
