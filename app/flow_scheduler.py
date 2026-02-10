"""Flow scheduler for automated batch processing with NEED_ACTION queue."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional


@dataclass
class CarCard:
    card_id: str
    batch_id: str
    status: str
    photo_files: List[str] = field(default_factory=list)
    photo_urls: List[str] = field(default_factory=list)
    template_id: str = "sale"
    ai_result: Optional[Dict] = None
    mapped_avito: Optional[Dict] = None
    post_url: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def log(self, message: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.logs.append(f"{timestamp} {message}")


@dataclass
class NeedActionItem:
    card_id: str
    batch_id: str
    reason: str
    requires_manual_confirmation: bool = True


@dataclass
class PublicationRecord:
    card_id: str
    batch_id: str
    post_url: Optional[str]
    status: str
    published_at: str


@dataclass
class FlowState:
    cards: Dict[str, CarCard] = field(default_factory=dict)
    need_action: List[NeedActionItem] = field(default_factory=list)
    history: List[PublicationRecord] = field(default_factory=list)
    processed_batches: set[str] = field(default_factory=set)

    def add_history(self, card: CarCard) -> None:
        self.history.append(
            PublicationRecord(
                card_id=card.card_id,
                batch_id=card.batch_id,
                post_url=card.post_url,
                status=card.status,
                published_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
        )

    def add_need_action(self, card: CarCard, reason: str) -> None:
        self.need_action.append(
            NeedActionItem(card_id=card.card_id, batch_id=card.batch_id, reason=reason)
        )

    def resolve_need_action(self, card_id: str) -> bool:
        before = len(self.need_action)
        self.need_action = [item for item in self.need_action if item.card_id != card_id]
        return len(self.need_action) < before


def _now_id(prefix: str, index: int) -> str:
    return f"{prefix}_{int(time.time())}_{index}"


@dataclass
class FlowScheduler:
    interval_minutes: int
    state: FlowState
    fetch_batches: Callable[[], List[str]]
    import_photos: Callable[[str], Dict]
    ai_client: Callable[[List[str], str], Dict]
    mapper: Callable[[Dict, List[str]], Dict]
    poster: Callable[[Dict, List[str]], Dict]

    def _ensure_card(self, batch_id: str, index: int) -> CarCard:
        card_id = _now_id("card", index)
        card = CarCard(card_id=card_id, batch_id=batch_id, status="NEW")
        self.state.cards[card_id] = card
        card.log("Card created")
        return card

    def _run_chain(self, card: CarCard) -> None:
        try:
            card.log("Importing photos")
            photo_result = self.import_photos(card.batch_id)
            card.photo_files = photo_result.get("photo_files", [])
            card.photo_urls = photo_result.get("photo_urls", [])
            card.status = "PHOTOS_READY"

            card.log("Running AI")
            ai_response = self.ai_client(card.photo_files, card.template_id)
            if ai_response.get("status") == "NEED_ACTION":
                card.status = "NEED_ACTION"
                card.errors.extend(ai_response.get("errors", []))
                self.state.add_need_action(card, "; ".join(ai_response.get("errors", [])) or "AI validation failed")
                return

            card.ai_result = ai_response.get("ai_result")
            card.status = "AI_READY"

            card.log("Mapping to Avito")
            mapped_response = self.mapper(card.ai_result or {}, card.photo_files)
            if mapped_response.get("status") == "NEED_ACTION":
                card.status = "NEED_ACTION"
                card.errors.extend(mapped_response.get("errors", []))
                self.state.add_need_action(card, "; ".join(mapped_response.get("errors", [])) or "Mapping failed")
                return

            card.mapped_avito = mapped_response.get("mapped_avito")
            card.status = "READY_TO_POST"

            card.log("Posting to Avito")
            post_response = self.poster(card.mapped_avito or {}, card.photo_files)
            status = post_response.get("status")
            card.post_url = post_response.get("post_url")

            if status == "POSTED":
                card.status = "POSTED"
                self.state.add_history(card)
            elif status == "NEED_ACTION":
                card.status = "NEED_ACTION"
                errors = post_response.get("errors", [])
                card.errors.extend(errors)
                reason = "; ".join(errors) or "Captcha or manual confirmation required"
                self.state.add_need_action(card, reason)
            else:
                card.status = "FAILED"
                card.errors.extend(post_response.get("errors", []))
        except Exception as exc:  # noqa: BLE001 - propagate flow errors
            card.status = "FAILED"
            card.errors.append(str(exc))

    def run_once(self) -> None:
        batch_ids = self.fetch_batches()
        new_batch_ids = [batch_id for batch_id in batch_ids if batch_id not in self.state.processed_batches]
        for index, batch_id in enumerate(new_batch_ids, start=1):
            card = self._ensure_card(batch_id, index)
            self._run_chain(card)
            self.state.processed_batches.add(batch_id)

    def run_cycles(self, cycles: int) -> None:
        for _ in range(cycles):
            self.run_once()
            time.sleep(self.interval_minutes * 60)

    def run_forever(self) -> None:
        while True:
            self.run_once()
            time.sleep(self.interval_minutes * 60)
