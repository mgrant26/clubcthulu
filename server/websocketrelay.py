import threading
import socket

try:
    #import asyncio
    asyncio = None
except ImportError:
    asyncio = None
try:
    #import websockets
    websockets = None
except ImportError:
    websockets = None

from server import ServerThread

class WebSocketServer(threading.Thread):
    """WebSocketServer thread for transporting websockets to local udp
    """
    def __init__(self, server: ServerThread, port: int, name: str = "wssthread"):
        super(WebSocketServer, self).__init__(name = name)
        
        self.server = server
        self.port = port
        self.clients = {}
        self.running = True
        self.block = None
        self.daemon = True
        self.ws = None
        self.start()

    def run(self):
        print("Starting WebSocket Relay...")
        if websockets and asyncio:
            self.block = asyncio.Event()
            asyncio.run(self.run_socket())
        else:
            message = ["asyncio" if not asyncio else "","websockets" if not websockets else ""]
            print(f'missing modules {", ".join(message)}')
        #self.ws = websockets.serve(self.redirect, self.server.ip, self.port)

    async def redirect(self, websocket):
        """Redirects WebSocket messages to the udp server
        """
        client = websocket.remote_address
        self.clients[(client[0], client[1])] = websocket
        try:
            async for message in websocket:
                self.server.process_websocket_message(message, (client[0],client[1]))
        finally:
            print("Websocket client disconnected")
            del self.clients[(client[0],client[1])]


    async def run_socket(self):
        """Runs the websocket server
        """

        #loop = asyncio.get_running_loop()
        #self.stop_event.set_result(None)
    
        async with websockets.serve(self.redirect, self.server.ip, self.port, family=socket.AF_INET) as ws:
            self.ws = ws
            try:
                await self.block.wait()
            finally:
                ws.close() 

    def stop(self):
        """Stops the websocket server
        """
        self.block.set()
        self.running = False
