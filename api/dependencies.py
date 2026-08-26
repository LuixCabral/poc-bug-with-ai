from fastapi import Request
from agno.agent import Agent


def get_agent(request: Request) -> Agent:
    return request.app.state.agent
