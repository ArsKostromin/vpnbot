# 🛡️ VPN Admin Panel — Django

Панель администратора для управления VPN‑ботом. Позволяет создавать и редактировать тарифы, подписки, пользователей, сервера, промокоды и обрабатывать логи. Используется в связке с Telegram‑ботом: [vpn-bot](https://github.com/ArsKostromin/vpn-bot).

---

## ⚙️ Основной функционал

### 👥 Пользователи
- Telegram ID, email, баланс, UUID
- Реферальная система
- История подписок и оплат

### 💳 Пополнение баланса
- Криптовалюта
- Robokassa
- Telegram Stars (через внешнюю ссылку)

### 🛰️ VPN-подписки
- Создаются через Telegram‑бота
- Привязываются к тарифам и пользователям
- UUID и VLESS-ссылка генерируются автоматически
- Поддержка паузы и авто‑продления
- Система скидок и промокодов

### 📦 Тарифы (Subscription Plans)
- Типы: `socials`, `torrents`, `secure`, `country`, `serfing`
- Продолжительность: `1m`, `3m`, `6m`, `1y`
- Цена, скидка, валюта
- Можно скрыть из Telegram‑бота

### 🌐 VPN‑Серверы
- Название и страна
- API‑URL (используется для выдачи конфигов и логов)
- Активность сервера
- Счётчик пользователей

### 📜 Логи
- Получение логов от FastAPI‑сервера
- Привязка логов к пользователям по UUID
- Просмотр логов трафика, подключений и запросов

### 🎁 Промокоды и скидки
- Управление кодами и сроками действия
- Автоматическая активация при покупке

---

## 🗃 Структура проекта

| Модель              | Назначение                            |
|---------------------|----------------------------------------|
| `VPNUser`           | Пользователь VPN                      |
| `Subscription`      | Подписка на VPN                       |
| `SubscriptionPlan`  | Тариф на VPN                          |
| `VPNServer`         | Сервер выдачи VLESS‑конфигов         |
| `ProxyLog`          | Запросы, переданные через прокси      |
| `PromoCode`         | Промокоды                             |

---

## 🔌 Интеграции

- [x] FastAPI сервер (для генерации конфигов и логов)
- [x] Telegram бот ([vpn-bot](https://github.com/ArsKostromin/vpn-bot))
- [x] Сервисы оплаты: Crypto, Robokassa, Stars

---

## 🛠 Развёртывание

1. Клонируй проект:

```bash
git clone https://github.com/ArsKostromin/vpnbot.git
cd vpnbot
```

2. Настрой `.env`:

```env
DEBUG=True
SECRET_KEY=your_secret
ALLOWED_HOSTS=your.domain.com

# База данных
DB_NAME=...
DB_USER=...
DB_PASSWORD=...

# FastAPI endpoints
XRAY_API_KEY=...
```

3. Установи зависимости:

```bash
pip install -r requirements.txt
```

4. Применить миграции и создать суперпользователя:

```bash
python manage.py migrate
python manage.py createsuperuser
```

5. Запустить сервер:

```bash
python manage.py runserver
```
ну или просто:

```bash
docker-compose up --build -d
```

---

## 🔒 Безопасность

- UUID и VLESS‑конфиги не передаются открыто
- Проксирование и логи доступны только через защищённый API
- Пароли хранятся безопасно, TLS на всех уровнях

---

## 📚 Связанные проекты

- 🧠 Telegram‑бот: [vpn-bot](https://github.com/ArsKostromin/vpn-bot)
- ⚡ FastAPI сервер: приватный (принимает запросы на генерацию конфигов и логов) https://github.com/ArsKostromin/fastapi_xray
- https://github.com/ArsKostromin/tg_stars
- https://github.com/ArsKostromin/vpnguide
- https://github.com/ArsKostromin/support_tg_bot
---

## 🤘 Автор

Проект сделан с расчётом на масштабируемость, автоматизацию и минимум ручного администрирования.

