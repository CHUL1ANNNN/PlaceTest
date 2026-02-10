# Модель данных «Карточка машины» (Task 4)

Цель: единый объект, который хранит всё по машине и двигается по статусам.

## CarCard

```yaml
CarCard:
  id: "cc_001"
  batch_id: "b_2024_10_15_001"
  status: "NEW"
  photo_urls:
    - "https://photo-site.example.com/storage/b_2024_10_15_001/01_exterior_front.jpg"
  photo_files:
    - "data/photos/cc_001/01_exterior_front.jpg"
  template_id: "sale"
  ai_result: {}
  mapped_avito: {}
  profile_id: "profile_01"
  post_url: null
  logs:
    - "2024-10-15T12:00:00Z: created"
  errors: []
```

### Поля

- `id` — уникальный идентификатор карточки.
- `batch_id` — связь с партией обработанных фото.
- `status` — текущий статус карточки.
- `photo_urls` — массив URL-ов готовых фото.
- `photo_files` — массив локальных путей (если файлы скачаны).
- `template_id` — идентификатор темы/шаблона.
- `ai_result` — результат ИИ (структура из `docs/ai-output-schema.md`).
- `mapped_avito` — результат маппинга в поля Авито.
- `profile_id` — профиль/аккаунт для публикации.
- `post_url` — ссылка на опубликованное объявление.
- `logs` — список событий/заметок по карточке.
- `errors` — список ошибок.

## Статусы и переходы

Базовая схема:

```
NEW → PHOTOS_READY → AI_READY → READY_TO_POST → POSTED
                       ↘
                        NEED_ACTION
                       ↘
                        FAILED
```

### Описание статусов

- `NEW` — карточка создана, фото ещё не готовы.
- `PHOTOS_READY` — фото получены и отсортированы.
- `AI_READY` — ИИ вернул структуру, прошли базовые проверки.
- `READY_TO_POST` — маппинг в Авито выполнен, всё готово к публикации.
- `POSTED` — объявление опубликовано, `post_url` заполнен.
- `NEED_ACTION` — нужна ручная проверка/доработка.
- `FAILED` — ошибка, публикация невозможна без вмешательства.

### Правила переходов

- `NEW` → `PHOTOS_READY`: выполнены условия готовности батча, `photo_urls` заполнен.
- `PHOTOS_READY` → `AI_READY`: `ai_result` валиден по схеме.
- `AI_READY` → `READY_TO_POST`: `mapped_avito` заполнен и прошёл проверки.
- `READY_TO_POST` → `POSTED`: объявление опубликовано, `post_url` заполнен.
- Любой статус → `NEED_ACTION`: бизнес-правило требует ручной проверки.
- Любой статус → `FAILED`: критическая ошибка или невозможность продолжить.
