import os

from dotenv import load_dotenv

load_dotenv()

REQUIRED_ENV = ["JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT_KEY"]


def validate_env() -> None:
    """Levanta EnvironmentError se alguma variável obrigatória estiver ausente."""
    missing = [v for v in REQUIRED_ENV if not os.environ.get(v)]
    if missing:
        raise EnvironmentError(
            f"Variáveis de ambiente ausentes: {', '.join(missing)}. Cheque o .env"
        )


validate_env()
