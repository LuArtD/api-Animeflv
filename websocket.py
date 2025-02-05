import asyncio
import websockets

async def listen():
    uri = "ws://localhost:8000/ws/progress/test123"
    async with websockets.connect(uri) as websocket:
        try:
            while True:
                message = await websocket.recv()
                print(f"📥 Mensaje recibido: {message}")
        except:
            print("❌ Conexión cerrada")

asyncio.run(listen())
