import asyncio
import websockets
import json
import time

class WebSocketProtocol:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.clients = set()

    # WebSocket Server
    async def server_handler(self, websocket):
        self.clients.add(websocket)
        print(f"New client connected: {websocket.remote_address}")
        try:
            async for message in websocket:
                print(f"Received message: {message}")
                try:
                    data = json.loads(message)
                    response = await self.process_message(data)
                    await self.broadcast(json.dumps(response))
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"error": "Invalid JSON"}))
        except websockets.exceptions.ConnectionClosed:
            print(f"Client disconnected: {websocket.remote_address}")
        finally:
            self.clients.remove(websocket)

    async def process_message(self, data):
        message_type = data.get("type", "unknown")
        payload = data.get("payload", {})
        
        if message_type == "ping":
            return {"type": "pong", "payload": {"timestamp": time.time()}}
        elif message_type == "message":
            return {"type": "message", "payload": {"text": payload.get("text", ""), "sender": "server"}}
        else:
            return {"type": "error", "payload": {"message": "Unknown message type"}}

    async def broadcast(self, message):
        if self.clients:
            tasks = []
            for client in self.clients:
                try:
                    if not client.is_closed:
                        tasks.append(client.send(message))
                except AttributeError:
                    # In case is_closed is unavailable, skip the client
                    continue
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def start_server(self):
        async with websockets.serve(self.server_handler, self.host, self.port):
            print(f"WebSocket server started on ws://{self.host}:{self.port}")
            await asyncio.Future()  # Infinite loop for the server

    # WebSocket Client
    async def client(self, message):
        uri = f"ws://{self.host}:{self.port}"
        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps(message))
                print(f"Client sent: {message}")
                response = await websocket.recv()
                print(f"Client received: {response}")
                return json.loads(response)
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Client connection error: {e}")
            return {"error": "Connection closed"}

async def main():
    protocol = WebSocketProtocol()

    # Run the server in the background
    server_task = asyncio.create_task(protocol.start_server())
    
    # Give the server time to start
    await asyncio.sleep(1)

    # Testing the client
    try:
        # Test 1
        ping_message = {"type": "ping", "payload": {}}
        response = await protocol.client(ping_message)
        print(f"Ping response: {response}")
        
        # Test 2
        text_message = {"type": "message", "payload": {"text": "Hello, WebSocket!"}}
        response = await protocol.client(text_message)
        print(f"Message response: {response}")
    finally:
        # Cancel the server task
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            print("Server task cancelled")

if __name__ == "__main__":
    asyncio.run(main())