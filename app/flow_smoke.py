"""Smoke test for Task 11 automated flow."""

from __future__ import annotations

from flow_scheduler import FlowScheduler, FlowState


BATCHES = [f"batch_{i}" for i in range(1, 6)]


def fetch_batches():
    return BATCHES


def import_photos(batch_id: str):
    return {
        "photo_files": [f"data/{batch_id}/01.jpg", f"data/{batch_id}/02.jpg"],
        "photo_urls": [f"https://photo/{batch_id}/01.jpg", f"https://photo/{batch_id}/02.jpg"],
    }


def ai_client(photo_files, template_id):
    return {
        "status": "AI_READY",
        "ai_result": {
            "title": "Demo car",
            "description": "Long enough description",
            "avito_fields": {
                "category": "Автомобили",
                "brand": "Brand",
                "model": "Model",
                "price_rub": 1000000,
                "city": "Москва",
                "body_type": "Седан",
                "drive_type": "Передний",
                "color": "Белый",
                "owners": 1,
                "payment_per_month_rub": 10000,
            },
        },
    }


def mapper(ai_result, photo_files):
    return {"status": "READY_TO_POST", "mapped_avito": ai_result}


def poster(mapped_avito, photo_files):
    batch_hint = photo_files[0].split("/")[1]
    # simulate captcha/manual stop for one machine
    if batch_hint == "batch_3":
        return {"status": "NEED_ACTION", "post_url": None, "errors": ["Captcha required"]}
    return {
        "status": "POSTED",
        "post_url": f"https://avito.ru/item/{batch_hint}",
        "errors": [],
    }


def main():
    state = FlowState()
    scheduler = FlowScheduler(
        interval_minutes=0,
        state=state,
        fetch_batches=fetch_batches,
        import_photos=import_photos,
        ai_client=ai_client,
        mapper=mapper,
        poster=poster,
    )

    scheduler.run_once()

    posted = [card for card in state.cards.values() if card.status == "POSTED"]
    need_action = [card for card in state.cards.values() if card.status == "NEED_ACTION"]

    assert len(posted) == 4, f"Expected 4 posted cards, got {len(posted)}"
    assert len(need_action) == 1, f"Expected 1 NEED_ACTION, got {len(need_action)}"
    assert len(state.history) == 4, f"Expected history for 4 cards, got {len(state.history)}"
    assert len(state.need_action) == 1, f"Expected queue size 1, got {len(state.need_action)}"

    print("Smoke OK: 5 cards processed, 4 POSTED, 1 NEED_ACTION (captcha)")


if __name__ == "__main__":
    main()
