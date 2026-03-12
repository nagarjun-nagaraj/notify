from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis
import asyncio
import json
import asyncpg
import os

app = FastAPI()

# config from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/notify")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")

# store active websocket connections and listener tasks
connected_users = {}
listener_tasks = {}


@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.create_pool(DATABASE_URL)


async def redis_listener(websocket: WebSocket, db):
    r = aioredis.Redis(host=REDIS_HOST, port=6379)
    pubsub = r.pubsub()
    await pubsub.subscribe("notifications")

    async for message in pubsub.listen():
        if message["type"] == "message":
            data = message["data"].decode("utf-8")
            payload = json.loads(data)
            user_id = payload["user_id"]
            text = payload["message"]

            # Save to database
            await db.execute(
                "INSERT INTO notifications (user_id, message) VALUES ($1, $2)",
                user_id, text
            )

            # Push to user if online
            if user_id in connected_users:
                user_ws = connected_users[user_id]
                await user_ws.send_text(text)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()
    await websocket.send_text("connected successfully")

    # store connection
    connected_users[user_id] = websocket
    print(f"user {user_id} connected")

    # cancel old listener task if exists
    if user_id in listener_tasks:
        listener_tasks[user_id].cancel()

    # create new listener task and track it
    task = asyncio.create_task(redis_listener(websocket, app.state.db))
    listener_tasks[user_id] = task

    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_text(f"echo: {message}")
    except WebSocketDisconnect:
        connected_users.pop(user_id, None)
        if user_id in listener_tasks:
            listener_tasks[user_id].cancel()
            listener_tasks.pop(user_id, None)
        print(f"user {user_id} disconnected")


@app.get("/notifications/{user_id}")
async def get_notifications(user_id: int):
    rows = await app.state.db.fetch(
        "SELECT id, user_id, message, created_at FROM notifications WHERE user_id=$1 ORDER BY created_at DESC",
        user_id
    )
    return [dict(row) for row in rows]