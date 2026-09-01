import os

from dotenv import load_dotenv

load_dotenv()

REQUIRED_ENV = ["NOTION_API_TOKEN"]
OPTIONAL_ENV = ["NOTION_ROOT_PAGE_ID"]


def validate_env() -> None:
    """Raises EnvironmentError if any required variable is missing."""
    missing = [v for v in REQUIRED_ENV if not os.environ.get(v)]
    if missing:
        raise EnvironmentError(
            f"Missing environment variables: {', '.join(missing)}. "
            "Check your .env file."
        )


validate_env()
