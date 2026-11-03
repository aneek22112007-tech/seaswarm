# Agents propose, humans dispose

A search for a fishing boat is a series of decisions that someone has to own. Who was aboard. Where the current has taken the hull. Which boat searches which patch of water. Whether the Coast Guard is called. Which paper the family files, and by which date. Software can prepare those choices. It should not make them.

SeaSwarm is a room for that division of work. Three agents sit in a Mattermost channel with the community leader and the family. They read the same thread the humans read. They answer in that thread. The record of who said what is the product.

## What an agent is allowed to do

The context agent may notice that a boat is overdue and put the situation on one screen: the crew, the hours out, the last heading, a drift cone, the daylight that is left. The cone is arithmetic. Leeway from the wind, plus the current, times the hours since the last fix. The agent does not invent the radius.

The options agent may cut that cone into sectors and offer three plans. Each plan has a coverage percentage, a time, a fuel figure, a cost in rupees, a daylight margin, and a risk flag when the arithmetic says the search would still be out in rough water after 16:30. A person can clear a sector, move a boat, or reject a plan. The agent re-plans from the rows it has. It will not put two boats on one sector, and it will say the conflict out loud instead of quietly overwriting the assignment.

The action agent may draft the escalation to the Coast Guard and the marine police, and it may match the family to the public schemes with a rules engine: district, licence, gear, crew, port, documents, deadline. The draft sits in the thread as pending. The scheme note sits beside it. A pinned checklist shows what is done and what is still a decision.

## What a human has to do

Nothing in that list sends a message outside the room, spends money, or closes the search. Those wait for a sentence in the thread:

`Approved — escalation`

The dash is the em dash used in the room, not a hyphen. The name on the Mattermost account has to carry the role. In the Harnai demo, Ramesh is the community leader and Sunita speaks for the family. Sunita can sign the scheme outreach, because that packet is for her household. She cannot sign the escalation. When she tries, the thread answers, in so many words, that only the community leader can approve it. The pending row stays pending. There is no second code path that "helps" by sending it anyway.

When Ramesh does sign, the gate stores his username, his role, the message id, and the time. Only then does the release get a line in the audit. The operation log can be edited. The event log cannot. An update or a delete of an event is rejected.

This is the whole argument. Agents propose. Humans dispose. The disposal is a sentence a specific person typed, and the archive can show it later to the family, the panchayat, or a reviewer who was not in the channel that afternoon.

## The afternoon the memory is switched off

Search software that forgets is dangerous in a different way. SeaSwarm can be started with persistence off. The agents then ignore the database and the earlier turns. Ask for a plan twice and the sectors are inserted twice. Ask Ramesh to sign and the approval is not stored, because the write was skipped. The same scenario with persistence on keeps three sectors and keeps his name on the escalation.

The two logs are checked in next to the script that produced them. They are there so a demo can show the failure, not so that anyone runs a real search that way. The default is persistence on. The audit export reads the tables themselves, so the trail a reviewer opens is the one the database holds: assignments, corrections, evidence, and every sign-off, with who did each one.

Sagar-4 in the demo is a scripted boat, with mock wind, tide, and schemes, on a fixed afternoon off Harnai. The shape of the room is what we would want on a real afternoon. The agents prepare the picture and the options. A named person decides. The thread remembers.
