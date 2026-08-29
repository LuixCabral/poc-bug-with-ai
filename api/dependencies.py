from fastapi import Request
from agno.team import Team


def get_agent(request: Request) -> Team:
    return request.app.state.team
