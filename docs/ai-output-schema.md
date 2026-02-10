# Спецификация формата ответа ИИ (Task 2)

Цель: ИИ возвращает не текст, а структуру, пригодную для автоматической загрузки в Авито.

## Формат (JSON)

```json
{
  "title": "Kia Rio, 2018",
  "description": "Продается Kia Rio 2018 года...",
  "specs": {
    "year": 2018,
    "transmission": "AT",
    "engine": "1.6",
    "horsepower": 123,
    "mileage_km": 85000
  },
  "equipment": {
    "comfort": ["Кондиционер", "Подогрев сидений"],
    "interior": ["Тканевый салон", "Регулировка руля"],
    "security": ["Иммобилайзер"],
    "exterior": ["Легкосплавные диски"],
    "assist": ["Парктроник"],
    "visibility": ["Датчик света"],
    "safety": ["ABS", "ESP"],
    "multimedia": ["Bluetooth", "USB"]
  },
  "avito_fields": {
    "category": "Автомобили",
    "brand": "Kia",
    "model": "Rio",
    "price_rub": 950000,
    "city": "Москва",
    "body_type": "Седан",
    "drive_type": "Передний",
    "color": "Белый",
    "owners": 2,
    "payment_per_month_rub": 15000
  }
}
```

## Поля

### Обязательные верхнеуровневые

- `title` (string) — заголовок объявления.
- `description` (string) — описание объявления.
- `specs` (object) — технические характеристики.
- `equipment` (object) — комплектация по разделам.
- `avito_fields` (object) — поля для Авито.

### specs

- `year` (number) — год выпуска.
- `transmission` (string) — КПП: `MT | AT | CVT | AMT`.
- `engine` (string) — двигатель (объём в литрах, например `1.6`).
- `horsepower` (number) — мощность в л.с.
- `mileage_km` (number) — пробег в км.

### equipment

Разделы должны присутствовать всегда (даже если массив пустой):

- `comfort` — Комфорт.
- `interior` — Салон.
- `security` — Охрана.
- `exterior` — Экстерьер.
- `assist` — Помощь.
- `visibility` — Обзор.
- `safety` — Безопасность.
- `multimedia` — Мультимедиа.

### avito_fields

Минимальный набор, используемый при публикации:

- `category` (string) — категория Авито.
- `brand` (string) — марка.
- `model` (string) — модель.
- `price_rub` (number) — цена в рублях.
- `city` (string) — город размещения.
- `body_type` (string) — тип кузова.
- `drive_type` (string) — тип привода.
- `color` (string) — цвет.
- `owners` (number) — количество владельцев.
- `payment_per_month_rub` (number) — платёж в месяц.

## Правила

1. **Пробег ≤ 160 000 км** (`specs.mileage_km`).
2. **Платёж** (`avito_fields.payment_per_month_rub`) **в диапазоне 5 000–25 000 руб.**
3. **Чек-лист обязателен** — все разделы `equipment` должны быть заполнены (минимум пустой массив).

## Валидаторы

Перед публикацией должны быть проверены:

- Наличие всех обязательных полей верхнего уровня: `title`, `description`, `specs`, `equipment`, `avito_fields`.
- `specs.mileage_km` — число и `<= 160000`.
- `avito_fields.payment_per_month_rub` — число и `>= 5000` и `<= 25000`.
- Все ключи `equipment` присутствуют и имеют тип `array`.
- `specs.year`, `specs.horsepower`, `avito_fields.price_rub`, `avito_fields.owners` — числа.
- `specs.transmission` — одно из `MT | AT | CVT | AMT`.
- `description` длиной не менее 200 символов (рекомендуемая проверка качества).
