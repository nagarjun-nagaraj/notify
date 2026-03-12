from fastapi import FastAPI, WebSocket
import redis.asyncio as aioredis
import asyncio

app = FastAPI()

async def redis_listener(websocket: WebSocket):
    r = aioredis.Redis(host='localhost', port=6379)
    pubsub = r.pubsub()
    await pubsub.subscribe("notifications")

    async for message in pubsub.listen():
        if message["type"] == "message":
            data = message["data"].decode("utf-8")
            await websocket.send_text(data)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("connected successfully")

    # Run both concurrently
    asyncio.create_task(redis_listener(websocket))

    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_text(f"echo: {message}")
    except Exception:
        pass  # client disconnected, exit cleanly