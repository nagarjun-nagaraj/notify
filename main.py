from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis
import asyncio
import json

app = FastAPI()

# store active websocket connections
connected_users = {}

async def redis_listener(websocket: WebSocket):
    r = aioredis.Redis(host='localhost', port=6379)
    pubsub = r.pubsub()
    await pubsub.subscribe("notifications")

    async for message in pubsub.listen():
        if message["type"] == "message":
            data = message["data"].decode("utf-8")

            # Parse JSON
            payload = json.loads(data)

            user_id = payload["user_id"]
            text = payload["message"]

            # Send only to the correct user
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

    # run redis listener in background
    asyncio.create_task(redis_listener(websocket))

    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_text(f"echo: {message}")

    except WebSocketDisconnect:
        # remove user on disconnect
        connected_users.pop(user_id, None)
        print(f"user {user_id} disconnected")