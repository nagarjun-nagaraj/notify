# notify

A real-time notification service: external services publish events, connected users receive them instantly via WebSocket. Missed notifications are persisted in PostgreSQL and retrievable via REST API.

## How it works

1. A client connects via WebSocket, identified by `user_id`
2. An external service publishes an event to a Redis channel
3. The notification service receives it and saves it to PostgreSQL
4. If the target user is online, the message is pushed instantly via WebSocket
5. If offline, the notification waits in the database until fetched

## Tech Stack

- **FastAPI** — WebSocket server and REST API
- **Redis Pub/Sub** — event delivery between services
- **PostgreSQL** — persistent notification storage
- **asyncpg** — async PostgreSQL driver
- **Docker Compose** — single command setup

## Getting Started

**Prerequisites:** Docker and Docker Compose
```bash
git clone https://github.com/nagarjun-nagaraj/notify.git
cd notify
docker compose up --build
```

That's it. No manual setup required.

## API Reference

**Connect via WebSocket**
```
WS /ws?user_id={id}
```

**Fetch stored notifications**
```
GET /notifications/{user_id}
```

**Publish a notification (from any service)**
```bash
docker exec -it notify-redis-1 redis-cli PUBLISH notifications '{"user_id": 42, "message": "your message here"}'
```

## Architecture
```
[ Any Service ]
      │
      │  PUBLISH to Redis channel
      ▼
[ Redis Pub/Sub ]
      │
      │  delivers to subscriber
      ▼
[ Notification Service ]
      │
      ├──▶ INSERT into PostgreSQL (always)
      │
      └──▶ WebSocket push (if user is online)
```