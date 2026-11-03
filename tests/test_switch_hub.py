"""Hub history and fan-out."""

from __future__ import annotations

import asyncio

from switch.events import actor_type_for, make_event
from switch.hub import Hub


def test_history_is_isolated_by_room():
    hub = Hub()
    hub.publish(make_event(room_id="sar-harnai", username="ramesh", text="overdue"))
    hub.publish(make_event(room_id="other", username="sunita", text="hello"))
    harnai = hub.history("sar-harnai")
    assert len(harnai) == 1
    assert harnai[0]["text"] == "overdue"
    assert hub.history("other")[0]["username"] == "sunita"


def test_history_returns_copies():
    hub = Hub()
    hub.publish(make_event(room_id="sar-harnai", username="ramesh", text="overdue"))
    hub.history("sar-harnai")[0]["text"] = "changed"
    assert hub.history("sar-harnai")[0]["text"] == "overdue"


def test_subscribe_receives_the_room_only():
    async def run():
        hub = Hub()
        queue = hub.subscribe("sar-harnai")
        hub.publish(make_event(room_id="other", username="ramesh", text="nope"))
        hub.publish(make_event(room_id="sar-harnai", username="sunita", text="missing"))
        item = await asyncio.wait_for(queue.get(), timeout=1)
        assert item["text"] == "missing"
        assert queue.empty()

    asyncio.run(run())


def test_update_rewrites_one_message():
    hub = Hub()
    event = hub.publish(make_event(room_id="sar-harnai", username="action", text="draft"))
    updated = hub.update("sar-harnai", event["message_id"], "draft v2")
    assert updated is not None
    assert updated["text"] == "draft v2"
    assert updated["edited"] is True
    assert hub.update("sar-harnai", "missing", "nope") is None


def test_subscribers_names_the_connected_agent():
    hub = Hub()
    queue = hub.subscribe("sar-harnai", "context")
    assert hub.subscribers("sar-harnai") == ["context"]
    hub.unsubscribe(queue)
    assert hub.subscribers("sar-harnai") == []


def test_actor_type_marks_agents():
    assert actor_type_for("context") == "agent"
    assert actor_type_for("ramesh") == "human"
    event = make_event(room_id="sar-harnai", username="options", text="plan")
    assert event["actor_type"] == "agent"
    assert event["message_id"] == event["id"]
