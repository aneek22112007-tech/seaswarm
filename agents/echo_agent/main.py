"""Echo agent process. The loop is disabled in tests via SEASWARM_DISABLE_LOOP."""

from agents.common.runner import serve
from agents.echo_agent.handler import handle_event

app = serve("echo", handle_event)
