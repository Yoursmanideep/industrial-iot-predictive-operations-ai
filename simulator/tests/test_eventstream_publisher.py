from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from industrial_sim.transport.eventstream import (
    EventstreamPublisherConfig,
    NullEventPublisher,
)


@dataclass(frozen=True)
class FakeEvent:
    event_id: str = "EVT-1"

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_time": datetime(2026, 9, 21, tzinfo=timezone.utc).isoformat(),
        }


def test_null_event_publisher_is_safe() -> None:
    publisher = NullEventPublisher()
    publisher.publish([FakeEvent()])
    publisher.close()


def test_eventstream_config_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv(
        "FABRIC_EVENTSTREAM_CONNECTION_STRING",
        "Endpoint=sb://example/",
    )
    config = EventstreamPublisherConfig.from_environment()
    assert config.connection_string == "Endpoint=sb://example/"
    assert config.fully_qualified_namespace is None
    assert config.eventhub_name is None
