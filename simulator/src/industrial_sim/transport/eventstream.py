from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Iterable, Protocol


class EventPublisher(Protocol):
    def publish(self, events: Iterable[object]) -> None:
        ...


@dataclass(frozen=True)
class EventstreamPublisherConfig:
    connection_string: str | None = None
    fully_qualified_namespace: str | None = None
    eventhub_name: str | None = None

    @classmethod
    def from_environment(cls) -> "EventstreamPublisherConfig":
        return cls(
            connection_string=os.getenv("FABRIC_EVENTSTREAM_CONNECTION_STRING"),
            fully_qualified_namespace=os.getenv("FABRIC_EVENTSTREAM_FQDN"),
            eventhub_name=os.getenv("FABRIC_EVENTSTREAM_ENTITY_NAME"),
        )


class EventHubEventstreamPublisher:
    """Publish simulator events to a Fabric Eventstream Custom Endpoint.

    The custom endpoint exposes an Event Hubs-compatible producer surface.
    Credentials are read from environment variables only.
    """

    def __init__(self, config: EventstreamPublisherConfig) -> None:
        self.config = config
        self._producer = self._build_producer()

    def _build_producer(self):
        try:
            from azure.eventhub import EventData, EventHubProducerClient
        except ImportError as exc:
            raise RuntimeError(
                "Eventstream publishing requires the simulator 'realtime' extra"
            ) from exc

        if self.config.connection_string:
            producer = EventHubProducerClient.from_connection_string(
                conn_str=self.config.connection_string,
            )
        elif (
            self.config.fully_qualified_namespace
            and self.config.eventhub_name
        ):
            try:
                from azure.identity import DefaultAzureCredential
            except ImportError as exc:
                raise RuntimeError(
                    "Entra ID publishing requires the simulator 'realtime' extra"
                ) from exc
            producer = EventHubProducerClient(
                fully_qualified_namespace=self.config.fully_qualified_namespace,
                eventhub_name=self.config.eventhub_name,
                credential=DefaultAzureCredential(),
            )
        else:
            raise ValueError(
                "Set FABRIC_EVENTSTREAM_CONNECTION_STRING or "
                "FABRIC_EVENTSTREAM_FQDN + FABRIC_EVENTSTREAM_ENTITY_NAME"
            )

        self._event_data_type = EventData
        return producer

    def publish(self, events: Iterable[object]) -> None:
        batch = self._producer.create_batch()
        has_events = False

        for event in events:
            payload = json.dumps(
                event.to_dict(),
                separators=(",", ":"),
                sort_keys=True,
            )
            try:
                batch.add(self._event_data_type(payload))
            except ValueError:
                if not has_events:
                    raise
                self._producer.send_batch(batch)
                batch = self._producer.create_batch()
                batch.add(self._event_data_type(payload))
            has_events = True

        if has_events:
            self._producer.send_batch(batch)

    def close(self) -> None:
        self._producer.close()


class NullEventPublisher:
    def publish(self, events: Iterable[object]) -> None:
        return None

    def close(self) -> None:
        return None
