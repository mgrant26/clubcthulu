"""World related classes
"""
import threading
import time

from math2 import Vector
from messagebuilder import MessageRelay
from clienthandler import ClientThread
import utils


class World(threading.Thread):
    """ World class
    """

    def __init__(self, name: str, message_handler: MessageRelay, client_handler: ClientThread,
                 width: int, height: int, chunk_width: int = 400, chunk_height: int = 400,
                 spawn_point: Vector = None, tps=20, threadname="worldthread"):
        super(World, self).__init__(name=threadname)
        self.name = name
        self.message_handler = message_handler
        self.client_handler = client_handler
        self.width = width
        self.height = height
        self.chunk_width = chunk_width
        self.chunk_height = chunk_height
        self.chunks = [[]]
        self.active_chunks = []
        self.clients = {}
        self.moved_clients = []
        if spawn_point is not None:
            self.spawn_point = spawn_point
        else:
            self.spawn_point = [0, 0]
        self.lock = threading.RLock()
        self.running = True
        self.tps = tps
        self.timer = utils.Timer()
        self.delta = 1-self.timer.get_delta().total_seconds()
        self.start()

    def run(self):
        print("Starting World Handler")
        with self.lock:
            self.chunks = self.create_empty_world()
            self.spawn_point = [int(self.width/2), int(self.height/2)]
        while self.running:
            with self.lock:
                self.delta = 1-self.timer.get_delta().total_seconds()
                for chunk in self.clients.items():
                    chunk[1].update_clients()
                self.send_positions()
                time.sleep(1.0/self.tps)

    def create_empty_world(self):
        """Generates a bunch of empty chunks
        """
        chunks = []
        for y in range(0, self.height):
            chunks.append([])
            for x in range(0, self.width):
                chunk = Chunk(self, x, y, self.chunk_width, self.chunk_height)
                chunks[y].append(chunk)
        return chunks

    def add_client(self, client):
        """Adds active client
        """
        with self.lock:
            chunk = self.chunks[self.spawn_point[1]][self.spawn_point[0]]
            self.clients[client] = chunk
            chunk.add_client(client)

    def remove_client(self, client):
        """Removes active client
        """
        with self.lock:
            self.clients.get(client).remove_client(client)
            self.clients.pop(client, None)

    def move_client(self, client, x, y) -> bool:
        """Moves a client to a new chunk
        """
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        with self.lock:
            if client.chunk[0] == x and client.chunk[1] == y:
                self.moved_clients.append(client)
                return True
            c_chunk = self.clients[client]
            new_chunk = self.chunks[int(y)][int(x)]

            c_chunk.remove_client(client)
            new_chunk.add_client(client)

            client.set_pos([client.pos[0] % self.chunk_width,
                           client.pos[1] % self.chunk_height])

            client.chunk = [int(new_chunk.x), int(new_chunk.y)]
            self.clients[client] = new_chunk
            self.moved_clients.append(client)
            return True

    def send_positions(self):
        """Updates all connected clients
        """
        with self.lock:
            for client in self.clients:
                for up in self.moved_clients:
                    self.send_client_position_to(up, client)
            self.moved_clients.clear()

    def full_update(self, target):
        """Fully updates all logged in clients
        """
        with self.lock:
            for client in self.clients:
                self.send_full_client_to(client, target)

    def send_full_client_to(self, client, target):
        """Sends full client information to the target
        """
        with self.lock:
            to_send = {
                "response": "client-update",
                "client-id": str(client.id),
                "client-name": client.name,
                "chunk-x": client.chunk[0],
                "chunk-y": client.chunk[1],
                "x": client.pos[0],
                "y": client.pos[1]
            }
            self.message_handler.send_message(target.get_addr(), to_send, 1)

    def send_client_position_to(self, client, target):
        """Sends client position to a target
        """
        with self.lock:
            to_send = {
                "response": "position-update",
                "target": str(client.id),
                "new-chunk-x": client.chunk[0],
                "new-chunk-y": client.chunk[1],
                "new-x": client.pos[0],
                "new-y": client.pos[1]
            }
            self.message_handler.send_message(target.get_addr(), to_send, 1)

    def stop(self):
        """ Stops this thread
        """
        self.running = False


class Chunk:
    """Chunk class
    Wraps chunk information
    Parameters:
    world: World
        World that the chunk exists in
    x: int
        X location within the world where this chunk exists
    y: int
        Y location within the world where this chunk exists
    width: int
        Width of this chunk
    height: int
        height of this chunk
    """

    def __init__(self, world: World, x: int, y: int, width: int, height: int):
        self.world = world
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.clients = []

    def add_client(self, client):
        """Adds a client to this chunk
        client: Client
            Client to add
        """
        self.clients.append(client)
        client.chunk = [self.x, self.y]

    def remove_client(self, client):
        """Removes a client from this chunk
        could be more efficient
        client: Client
            Client to remove
        """
        if client in self.clients:
            self.clients.pop(self.clients.index(client))

    def update_clients(self):
        """Attempts to update all clients within this chunk"""
        for c in self.clients:
            self.update_client(c)

    def update_client(self, c):
        """Updates the positioning of the specified client
        parameters:
        c: Client
            Client to update
        """
        if c.vel is None or (c.vel[0] == 0 and c.vel[1] == 0):
            return
        # Holds the original x position of the client
        hold_x = int(c.pos[0] + c.vel[0] * self.world.delta)
        # Holds the original y position of the client
        hold_y = int(c.pos[1] + c.vel[1] * self.world.delta)
        # Clamps the x position to the width of the chunk
        next_x = int(c.pos[0] + c.vel[0] * self.world.delta) % self.width
        # Clamps the y position to the width of the chunk
        next_y = int(c.pos[1] + c.vel[1] * self.world.delta) % self.height

        # If any of the holds don't match, client has moved.
        if next_x != hold_x or next_y != hold_y:
            n_x = int(hold_x // self.width)  # Gets the new chunk X
            n_y = int(hold_y // self.height)  # Gets the new chunk Y
            # Attempts to move the client
            if self.world.move_client(c, self.x + n_x, self.y+n_y):
                c.pos = [int(next_x), int(next_y)]  # Sets the client position
            else:
                c.pos = [max(0, min(c.pos[0] + c.vel[0], self.width)),
                         max(0, min(c.pos[1] + c.vel[1], self.height))]
        else:
            c.pos = [int(hold_x), int(hold_y)]
            self.world.move_client(c, self.x, self.y)
