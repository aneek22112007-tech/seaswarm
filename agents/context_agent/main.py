"""Context agent process."""

from agents.common.runner import serve
from agents.context_agent.handler import handle_event

app = serve("context", handle_event)
