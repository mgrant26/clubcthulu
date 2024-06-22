"""Provides functions and utilities for working with JSON data in Python.
"""

from uuid import UUID
from datetime import datetime, timedelta

import json
import secrets
import threading
import time

from math2 import Vector


class Client:
    """Client class

    Holds information about clients

    Parameters:
    id : UUID
        ID of the client, same as stored within the database
    name : str
        The clients name, pulled from the database and set upon registration
    last_response: datetime
        last timestamp when a message was recieved from this client
    addr : pair(str, int)
        The address from where the client sends messages from
    chunk : Vector
        The current chunk th client is in
    pos : Vector
        The current position of the client, for game client use
    privilege_level : int
        The privilege level of a client
        Used for command executions

    Functions:
    move:
        Adds a vector to the current position and updates chunk position
    teleport:
        Sets the position vector and updates chunk position
    set_addr:
        Sets self.addr
    get_addr:
        Returns self.addr
    get_session:
        Returns self.session
    to_json:
        Quick way to convert to json
    """

    def __init__(self, cid: UUID,  name: str, last_response: datetime, addr=("", 0),
                 chunk: Vector = None, pos: Vector = None, privilege_level: int = 0,
                 color: int = (0,0,0)):
        self.id = cid
        self.name = name
        self.last_response = last_response
        self.session = secrets.token_urlsafe(16)
        self._privilege_level = privilege_level
        self.addr = addr
        self.pos = pos if pos is not None else [0, 0]
        self.chunk = chunk if chunk is not None else [0, 0]
        self.vel = [0, 0]
        self.color = color
        self.moving = False

    def move(self, vel: Vector):
        """Adds a vector to the current position
        also updates chunk position
        Parameters:
        vel: Vector
            the vector to add
        chunk:
            the chunk to update using
        """
        # self.pos = [self.pos[0] + vel[0], self.pos[1] + vel[1]]
        self.vel = vel

    def teleport(self, vel: Vector, chunk):
        """Sets the current position to a vector
        also updates chunk position
        Parameters:
        vel: Vector
            The vector to use
        chunk: Chunk
            the chunk to update using
        """
        self.pos = vel
        chunk.update_client(self)

    def set_addr(self, addr):
        """Sets the client's address
        Parameters:
        addr: pair(str, int)
            The address to use"""
        self.addr = addr

    def get_addr(self):
        """Returns the client's address
        Returns:
        pair(str, int):
            The value of self.addr
        """
        return self.addr

    def get_session(self):
        """Returns the client's session id
        Returns:
        str:
            The session string of the client
        """
        return self.session

    def get_pos(self):
        """Returns the current position
        Returns:
        Vector:
            The position vector
        """
        return self.pos

    def set_pos(self, pos):
        """Sets the current position without a chunk update
        Parameters:
        pos: Vector:
            Vector to use
        """
        self.pos = pos

    @property
    def privilege_level(self):
        """
        Returns the privilege level of the object.

        This method returns the privilege level associated with the object. 
        It retrieves the privilege level stored in the '_privilege_level' attribute.

        Returns:
        int: The privilege level of the object.
        """
        return self._privilege_level

    @privilege_level.setter
    def privilege_level(self, other):
        raise AttributeError(
            'You cannot set privilege after client initialization')

    def to_json(self):
        """Dumps self to json string
        """
        return json.dumps(self.__dict__)


class ClientThread(threading.Thread):
    """The Client Thread
    Handles all clients

    Parameters:
    dc_time: timedelta Optional
        The amount of time between responses before a client is kicked
    clbk : func Optional
        Callback function to tell main thread information
    name : str Optional
        The name of the thread
        default: clientthread

    Functions:
    run:
        runs update_all() constantly
        Could be done on a timer in order to improve performance
    list_clients:
        Returns a string of all client names
    send_message_to_all:
        sends a supplied message to all connected clients
    update_all:
        performs update_client on all connected clients
    update_client:
        Sends periodic updates to clients
        Also kicks clients who haven't responded in a while
    get_client:
        returns client with given name or id
    get_client_ses:
        returns client using session string
    add_client:
        adds a client to the client maps
    update_client_ts:
        updates the timestamp of specific client
    update_client_bses_ts:
        updates the timestamp of specific client using session as an indentifier 
    remove_client_ses:
        removes a client based on session
    remove_client:
        removes a client based on id or name
    kick_client:
        sends a kick message to a client and removes them from the maps
    stop:
        sets self.running to false
        ends the loop within run
    """

    def __init__(self, server, dc_time=timedelta(minutes=5), clbk=None, name="clientthread"):
        super(ClientThread, self).__init__(name=name)
        self.clbk = clbk
        self.daemon = True
        self.dc_time = dc_time
        self.client_list = {}
        self.client_list_name = {}
        self.client_list_session = {}
        self.lock = threading.RLock()
        self.server = server
        self.running = True
        self.start()

    def run(self):
        """The main loop for the client handler
        """
        print("Starting Client Handler...")
        while self.running:
            self.update_all()
            time.sleep(0.0001)
        with self.lock:
            for client in self.client_list.copy().values():
                self.kick_client(client, "Server is closing.")

    def list_clients(self):
        """Returns a list of all connected clients
        waits for a lock
        """
        with self.lock:
            return {name: client.id for name, client in self.client_list_name.items()}

    def send_message_to_all(self, message, message_handler):
        """Sends the supplied message to all connected clients
        Parameters:
        message: dict
            The message to send
        message_handler: MessageThread
            The message handler to send the message through
        """
        with self.lock:
            for client in self.client_list.values():
                message_handler.send_message(client.get_addr(), message)

    def update_all(self):
        """Updates all connected clients
        """
        with self.lock:
            for client in self.client_list.copy().values():
                self.update_client(client)

    def update_client(self, client) -> bool:
        """Updates the specified client
        Used to track whether or not the client is connected or afk
        Parameters:
        client: Client
            Client to update
        """
        if not isinstance(client.last_response, datetime):
            return
        temp_time = datetime.now() - client.last_response
        if temp_time > self.dc_time:
            self.kick_client(client.name.lower(), "Session timed out.")
            return False
        return True

    def get_client(self, data) -> Client:
        """ Returns the client instance 
        Parameters:
        data: Any
            If the data is a string or a UUID attempts to pull from the relative maps otherwise
            returns None
        """
        with self.lock:
            if isinstance(data, str):
                return self.client_list_name.get(data.lower())
            elif isinstance(data, UUID):
                return self.client_list.get(data)
            return None

    def get_client_ses(self, session: str) -> Client:
        """ Returns the client instance based on session id
        Parameters:
        session: str
            the session id to use
        """
        with self.lock:
            return self.client_list_session.get(session)

    def add_client(self, client: Client) -> bool:
        """ Adds a client instance to the maps and alerts all connected clients
        Parameters:
        client: Client
            The client to insert
        """
        with self.lock:
            if client.name.lower() in self.client_list_name:
                return False
            self.client_list_name[client.name.lower()] = client
            self.client_list[client.id] = client
            self.client_list_session[client.get_session()] = client
            self.server.world_handler.add_client(client)
            self.send_message_to_all({
                "response": "client-joined",
                "client-name": client.name,
                "client-id": str(client.id),
                "x": client.pos[0],
                "y": client.pos[1],
                "chunk-x": client.chunk[0],
                "chunk-y": client.chunk[1]
            }, self.server.message_handler)
            print(f'{client.name} joined.')
            return True

    def update_client_ts(self, data) -> bool:
        """Updates the last response timestamp of a client
        Parameters:
        data: Any
            Attempts to update the client timestamp based on either name
            or UUID depending on the type
            otherwise it will always return False
        """
        with self.lock:
            client = None
            if isinstance(data, str):
                client = self.client_list_name.get(data.lower())
            elif isinstance(data, UUID):
                client = self.client_list.get(data)
            if client:
                client.last_response = datetime.now()
                return True
            return False

    def update_client_bses_ts(self, session: str) -> bool:
        """Updates the last response timestamp of a client
        Based on the session id
        Parameters:
        session: str
            the session id to lookup
        """
        with self.lock:
            client = self.client_list_session.get(session)
            if client is not None:
                res = self.update_client_ts(client.name.lower())
                return res
            return False

    def remove_client_ses(self, session: str) -> bool:
        """Removes a client instance based on the session id
        Sends a client-left packet to all connected clients
        Parameters:
        session: str
            The session id of the client to kick
        """
        with self.lock:
            client = self.client_list_session.pop(session, None)
            if client:
                self.send_message_to_all({
                    "response": "client-left",
                    "id": str(client.id)
                }, self.server.message_handler)
                name = client.name
                self.client_list.pop(client.id, None)
                self.client_list_name.pop(name.lower(), None)
                self.server.world_handler.remove_client(client)
                print(f'{name} left.')
            return True

    def remove_client(self, data) -> bool:
        """Removes a client instance based on name or uuid
        calls remove_client_ses() and get_client()
        Parameters:
        data: Any
            Used to call get_client()
        """
        with self.lock:
            client = self.get_client(data)
            if client:
                return self.remove_client_ses(client.session)
            return False

    def kick_client(self, client: Client, message: str = ""):
        """Kicks the supplied client off of the server
        Optionally sends a special message
        Parameters:
        client: Client
            Client to kick
        message: str
            Optional message to send
        """
        with self.lock:
            if ((isinstance(client, str) and client.lower() in self.client_list_name)
                    or client.name in self.client_list_name):
                if isinstance(client, str):
                    client = self.client_list_name.get(client)
                print(f"Kicking {client.name}")
                self.clbk('kick', {
                    'addr': client.get_addr(),
                    'message': message
                })
                self.remove_client(client.name.lower())

    def stop(self):
        """Stops the client thread"""
        self.running = False
