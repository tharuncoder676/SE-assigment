"""A minimal in-process publish/subscribe bus.

The booking service does not call the notification service directly; it
publishes an ``appointment.booked`` event and returns. Subscribers run on a
background thread pool, so a slow notification channel can never add latency
to the booking request. The interface deliberately mirrors that of a broker
(RabbitMQ / Kafka), so replacing this class with a real broker later is a
change of implementation, not of the calling code.
"""
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List

log = logging.getLogger("smartcare.events")


class EventBus:
    def __init__(self, workers: int = 4) -> None:
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = defaultdict(list)
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="event")
        self.published = 0

    def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        self._subscribers[topic].append(handler)

    def publish(self, topic: str, payload: Dict[str, Any], sync: bool = False) -> None:
        self.published += 1
        log.info("event published", extra={"event": topic})
        for handler in self._subscribers[topic]:
            if sync:
                self._run(handler, topic, payload)
            else:
                self._pool.submit(self._run, handler, topic, payload)

    @staticmethod
    def _run(handler, topic, payload) -> None:
        try:
            handler(payload)
        except Exception:                                  # pragma: no cover
            log.exception("subscriber failed", extra={"event": topic})

    def shutdown(self) -> None:
        self._pool.shutdown(wait=True)


bus = EventBus()
