"""Options agent process."""

from agents.common.runner import serve
from agents.options_agent.handler import handle_event

app = serve("options", handle_event)
