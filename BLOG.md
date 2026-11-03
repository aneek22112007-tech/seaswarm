# Agents propose, humans dispose

A search for a fishing boat is a series of decisions that someone has to own. Who was aboard. Where the current has taken the hull. Which boat searches which patch of water. Whether the Coast Guard is called. Which paper the family files, and by which date. Software can prepare those choices. It should not make them.

SeaSwarm is a room for that division of work. Three agents sit in a Mattermost channel with the community leader and the family. They read the same thread the humans read. They answer in that thread. The record of who said what is the product.

## What an agent is allowed to do

The context agent may notice that a boat is overdue and put the situation on one screen: the crew, the hours out, the last heading, a drift cone, the daylight that is left. The cone is arithmetic. Leeway from the wind, plus the current, times the hours since the last fix. The agent does not invent the radius.

The options agent may cut that cone into sectors and offer three plans. Each plan has a coverage percentage, a time, a fuel figure, a cost in rupees, a daylight margin, and a risk flag when the arithmetic says the search would still be out in rough water after 16:30. A person can clear a sector, move a boat, or reject a plan. The agent re-plans from the rows it has. It will not put two boats on one sector, and it will say the conflict out loud instead of quietly overwriting the assignment.

The action agent may draft the escalation to the Coast Guard and the marine police, and it may match the family to the public schemes with a rules engine: district, licence, gear, crew, port, documents, deadline. The draft sits in the thread as pending. The scheme note sits beside it. A pinned checklist shows what is done and what is still a decision.
