"""Mini control panel for managing CarCard workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse


@dataclass
class CarCard:
    card_id: str
    status: str
    photo_urls: List[str] = field(default_factory=list)
    ai_result: Optional[Dict] = None
    mapped_avito: Optional[Dict] = None
    post_url: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    needs_action: bool = False

    def log(self, message: str) -> None:
        timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        self.logs.append(f"{timestamp}: {message}")


CARDS: Dict[str, CarCard] = {
    "cc_demo": CarCard(
        card_id="cc_demo",
        status="NEW",
        photo_urls=[],
        ai_result=None,
        mapped_avito=None,
        post_url=None,
        logs=["Demo card created"],
        needs_action=False,
    )
}


def _render_index(selected_id: str) -> str:
    selected = CARDS.get(selected_id)

    def card_row(card: CarCard) -> str:
        need_action = (
            '<div class="need-action">Нужно действие</div>' if card.needs_action else ""
        )
        return (
            "<div class=\"card-item\">"
            f"<div><strong>{escape(card.card_id)}</strong></div>"
            f"<div class=\"status\">Статус: {escape(card.status)}</div>"
            f"{need_action}"
            "<div class=\"actions\">"
            f"<form method=\"get\" action=\"/\">"
            f"<input type=\"hidden\" name=\"card\" value=\"{escape(card.card_id)}\" />"
            "<button type=\"submit\">Открыть</button>"
            "</form>"
            f"<form method=\"post\" action=\"/action/{escape(card.card_id)}/download\">"
            "<button type=\"submit\">Скачать фото</button>"
            "</form>"
            f"<form method=\"post\" action=\"/action/{escape(card.card_id)}/ai\">"
            "<button type=\"submit\">AI</button>"
            "</form>"
            f"<form method=\"post\" action=\"/action/{escape(card.card_id)}/publish\">"
            "<button type=\"submit\">Публиковать</button>"
            "</form>"
            "</div>"
            "</div>"
        )

    cards_html = "".join(card_row(card) for card in CARDS.values())
    detail_html = "<p>Выберите карточку в очереди.</p>"

    if selected:
        photos = (
            "<ul>"
            + "".join(f"<li>{escape(url)}</li>" for url in selected.photo_urls)
            + "</ul>"
            if selected.photo_urls
            else "<p>Фото пока нет.</p>"
        )
        ai_result = (
            f"<pre>{escape(str(selected.ai_result))}</pre>"
            if selected.ai_result
            else "<p>ИИ ещё не запускался.</p>"
        )
        preview = (
            f"<p><strong>{escape(selected.ai_result.get('title', ''))}</strong></p>"
            f"<p>{escape(selected.ai_result.get('description', ''))}</p>"
            if selected.ai_result
            else "<p>Пока нет текста.</p>"
        )
        logs = "".join(f"<div>{escape(line)}</div>" for line in selected.logs)
        post_url = (
            f"<p><strong>Ссылка:</strong> <a href=\"{escape(selected.post_url)}\">"
            f"{escape(selected.post_url)}</a></p>"
            if selected.post_url
            else ""
        )
        detail_html = f"""
        <div class="section">
          <h2>Карточка машины: {escape(selected.card_id)}</h2>
          <p><span class="status">Статус:</span> {escape(selected.status)}</p>
          {post_url}
          <div class="actions">
            <form method="post" action="/action/{escape(selected.card_id)}/need_action">
              <button type="submit">Нужно действие</button>
            </form>
            <form method="post" action="/reset/{escape(selected.card_id)}">
              <button type="submit">Сбросить</button>
            </form>
          </div>
        </div>

        <div class="section">
          <h3>Фото</h3>
          {photos}
        </div>

        <div class="section">
          <h3>Результат ИИ</h3>
          {ai_result}
        </div>

        <div class="section">
          <h3>Предпросмотр текста</h3>
          {preview}
        </div>

        <div class="section">
          <h3>Логи публикации</h3>
          <div class="log">{logs}</div>
        </div>
        """

    return f"""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <title>Mini Control Panel</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    .layout {{ display: grid; grid-template-columns: 280px 1fr; gap: 24px; }}
    .card-list {{ border: 1px solid #ddd; padding: 12px; }}
    .card-item {{ padding: 8px; border-bottom: 1px solid #eee; }}
    .card-item:last-child {{ border-bottom: none; }}
    .status {{ font-weight: bold; }}
    .actions {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }}
    button {{ padding: 6px 10px; }}
    .section {{ border: 1px solid #ddd; padding: 12px; margin-bottom: 16px; }}
    .log {{ background: #f7f7f7; padding: 8px; border-radius: 4px; }}
    .need-action {{ color: #b00020; font-weight: bold; }}
  </style>
</head>
<body>
  <h1>Мини-панель управления</h1>

  <div class="layout">
    <div class="card-list">
      <h2>Очередь карточек</h2>
      {cards_html}
    </div>

    <div>
      {detail_html}
    </div>
  </div>
</body>
</html>
"""


class ControlPanelHandler(BaseHTTPRequestHandler):
    def _redirect(self, location: str) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        selected = params.get("card", ["cc_demo"])[0]
        body = _render_index(selected)
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            self._redirect("/")
            return

        if parts[0] == "action" and len(parts) == 3:
            _, card_id, action = parts
            card = CARDS.get(card_id)
            if card is None:
                self._redirect("/")
                return

            if action == "download":
                card.status = "PHOTOS_READY"
                card.photo_urls = ["https://photo-site.example.com/demo/01.jpg"]
                card.log("Photos downloaded")
            elif action == "ai":
                card.status = "AI_READY"
                card.ai_result = {
                    "title": "Demo car",
                    "description": "Demo description",
                }
                card.log("AI result generated")
            elif action == "publish":
                card.status = "POSTED"
                card.post_url = "https://avito.example.com/item/demo"
                card.log("Listing published")
            elif action == "need_action":
                card.status = "NEED_ACTION"
                card.needs_action = True
                card.log("Manual action required")
            else:
                card.log(f"Unknown action: {action}")

            self._redirect(f"/?card={card_id}")
            return

        if parts[0] == "reset" and len(parts) == 2:
            _, card_id = parts
            card = CARDS.get(card_id)
            if card:
                card.status = "NEW"
                card.photo_urls = []
                card.ai_result = None
                card.mapped_avito = None
                card.post_url = None
                card.needs_action = False
                card.logs = ["Reset card"]
            self._redirect(f"/?card={card_id}")
            return

        self._redirect("/")


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = HTTPServer((host, port), ControlPanelHandler)
    print(f"Control panel running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
