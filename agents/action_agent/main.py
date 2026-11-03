"""Action agent process. The follow-up loop starts only when the event loop is on."""

from agents.action_agent.followup import followup_loop
from agents.action_agent.handler import handle_event
from agents.common.runner import serve

app = serve("action", handle_event, extras=[followup_loop])
