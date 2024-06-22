"""
Server Main File
"""
import sys
import os
import socket
import threading
import sqlite3
import json
import base64
import traceback
from typing import Union
from uuid import UUID, uuid4
from datetime import datetime
import bcrypt
import rsa

import world
import websocketrelay

from clienthandler import Client, ClientThread
from command import Command, CommandProcessor
from messagebuilder import MessageRelay, build_message_generic

server = []


def get_server_thread():
    """Returns the server thread.
    """
    return server[0]


class InputThread(threading.Thread):
    """ Input Thread
    """
    running = True

    def __init__(self, clbk=None, name='inputthread'):
        self.clbk = clbk
        super(InputThread, self).__init__(name=name)
        self.daemon = True
        self.start()

    def run(self):
        while self.running:
            try:
                if os.isatty(sys.stdin.fileno()):
                    for line in sys.stdin:
                        self.clbk(line)
                else:
                    pass
            except EOFError as ex:
                print(ex)
                self.running = False
                self.clbk("end")
            except KeyboardInterrupt as ex:
                print(ex)
                self.running = False
                self.clbk("end")
            except IOError as ex:
                print(ex)
                self.running = False

    def stop(self):
        """ Stops this thread
        """
        self.running = False


class ServerThread(threading.Thread):
    """ The Main Server Thread
    """
    requests = {}
    keyboard = None
    running = True

    def __init__(self, ip=None, port=None,  name='serverthread'):
        super(ServerThread, self).__init__(name=name)
        self.ip = ip
        self.port = port
        self.keyboard = InputThread(self.input_clbk)
        self.init_requests()
        (self.publickey, self.privatekey) = rsa.newkeys(1024)
        self.p_key = self.publickey.save_pkcs1().decode('utf-8')
        self.sock = None
        self.message_handler = None
        self.client_handler = None
        self.world_handler = None
        self.database = None
        self.database_cur = None
        self.server_client = None
        self.command_processor = None
        self.websocket_relay = None
        self.start()

    def init_requests(self):
        """Initializes Request Handlers
        """
        self.requests["init-session"] = self.init_session
        self.requests["end-session"] = self.end_session
        self.requests["message"] = self.message
        self.requests["update"] = self.update_clients
        self.requests["confirm"] = self.confirm
        self.requests["ping"] = self.ping
        self.requests["obtain-public"] = self.sendkey
        self.requests["register"] = self.register
        self.requests["move"] = self.move
        self.requests["end-move"] = self.end_move

    def connect_databases(self):
        """Connects to the database
        """
        self.database = sqlite3.connect("data.db", check_same_thread=False)
        self.database_cur = self.database.cursor()

        self.database_cur.execute(
            """CREATE TABLE IF NOT EXISTS
            messages(id BLOB PRIMARY KEY, timestamp TEXT,
            message VARCHAR(255), user_id BLOB NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id))"""
        )
        self.database_cur.execute(
            """CREATE TABLE IF NOT EXISTS
            users(id BLOB PRIMARY KEY, name VARCHAR(32) NOT NULL UNIQUE COLLATE NOCASE
            , password VARCHAR(255)
            NOT NULL)"""
        )
        self.database_cur.execute(
            """CREATE TABLE IF NOT EXISTS 
            permissions(id BLOB PRIMARY KEY, privilege_level INT NOT NULL, FOREIGN KEY(id) 
            REFERENCES users (id))"""
        )

        self.database.commit()
        print("Database connected")

    def close_databases(self):
        """Closes the database connection
        """
        self.database.close()

    def setup_commands(self):
        """ Sets up usuable commands
        """
        self.server_client = Client(
            UUID(int=1), "SERVER", datetime.now(), privilege_level=99)
        self.command_processor = CommandProcessor([
            Command('commands', lambda args, executor: (
                print('-=COMMANDS=-'),
                [print(f'{name} {"".join(["<"+arg+">" for arg in command.params])}')
                 for (name, command) in get_server_thread().command_processor.commands.items()]
            )),
            Command('end', lambda args, executor: (
                print("Stopping server"),
                get_server_thread().close_server() if get_server_thread() is not None else 0
            ), 99),
            Command('printqueue', lambda args, executor: (
                print(get_server_thread().message_handler.get_waiting())
            ), 99),
            Command('listplayers', lambda args, executor: (
                print(get_server_thread().client_handler.list_clients())
            )),
            Command('kick', lambda args, executor: (
                print("Not enough arguments") if len(args) < 1 else (
                    client := get_server_thread().client_handler.get_client(args[0]),
                    get_server_thread().client_handler.kick_client(client,
                                                                   f'Kicked by {executor.name}') if client is not None
                    else print(f"{args[0]} is not logged in.")
                )
            ), 'name', 10)
        ],
            {
                "list": "listplayers",
                "lp": "listplayers",
                "online": "listplayers",
                "stop": "end",
                "die": "end",
                "q": "end",
                "quit": "end"
        })

    def run(self):
        print("Starting server")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(1)
        self.sock.settimeout(5)
        self.sock.bind((self.ip, self.port))
        self.connect_databases()
        self.setup_commands()
        self.websocket_relay = websocketrelay.WebSocketServer(self, self.port)
        self.message_handler = MessageRelay(self.sock, self.websocket_relay)
        self.client_handler = ClientThread(self, clbk=self.client_clbk)
        self.world_handler = world.World(
            "WorldName", self.message_handler, self.client_handler, 64, 64)
        try:
            while self.running:
                if ((self.sock is None or self.sock.fileno() == -1)
                        or not self.running or not self.keyboard.is_alive()):
                    break
                try:
                    data, addr = self.sock.recvfrom(1024)
                except ConnectionResetError:
                    continue
                except BlockingIOError:
                    continue
                except TimeoutError:
                    continue
                except OSError as ex:
                    if self.running:
                        print(f"Server error: {ex}")
                        print(traceback.format_exc())
                    continue
                if not data:
                    continue
                self.decode_json(data, addr)

                # self.sock.sendto(b'Message Recieved', addr)
                # print("message: %s" % data.decode('utf-8'))
        except OSError as ex:
            print(f"Server error: {ex}")
            print(traceback.format_exc())
            self.running = False
        self.stop_all_threads()
        self.sock.close()
        self.close_databases()

    def decode_json(self, data, addr):
        """Decodes recieved json files
        """
        try:
            dat = json.loads(data.decode('utf-8'))
            request = dat["request"]
            if "session-id" in dat:
                res = self.client_handler.update_client_bses_ts(
                    dat["session-id"])
                if res is False:
                    self.message_handler.send_message(addr, build_message_generic(
                        'info', 'kicked', 'You were not connected to the servr.'))
                    return False
            return self.requests[request](dat, addr)
        except ValueError:
            error_response = build_message_generic(
                "error", "malformed-data", 'Supplied data was invalid.')
            self.message_handler.send_message(addr, error_response)
            print("Error: Malformed data.")
            print(traceback.format_exc())
        except KeyError:
            error_response = build_message_generic(
                "error", "invalid-request", f'{request} is not a valid request type.')
            self.message_handler.send_message(addr, error_response)
            print(f'Error: {request} is not a valid request type.')
            print(traceback.format_exc())
        except OSError as ex:
            error_response = build_message_generic(
                "error", "internal-error", 'An internal server error has occurred')
            self.message_handler.send_message(addr, error_response)
            print(f'Error: {ex}')
            print(traceback.format_exc())

    def init_session(self, data, addr) -> bool:
        """Initializes user sessions
        """
        print('initing session')
        username = data['username']
        password = data['password']

        pres = self.database_cur.execute(
            "SELECT password FROM users WHERE name = (?) LIMIT 1", (username,))
        passw = pres.fetchone()

        if passw is None or passw[0] is None:
            error_response = build_message_generic(
                "error", "invalid-info", 'Username was invalid.')
            self.message_handler.send_message(addr, error_response)
            return False

        try:
            password = rsa.decrypt(base64.b64decode(password), self.privatekey)
        except rsa.pkcs1.DecryptionError:
            error_response = build_message_generic(
                "error", "failed-decrypt", "Failed to decrypt password: Try reconnecting.")
            self.message_handler.send_message(addr, error_response)
            return False

        if bcrypt.checkpw(password, passw[0]):
            req = self.database_cur.execute(
                "SELECT id, name FROM users WHERE name = (?) LIMIT 1", (username,))
            val = req.fetchone()
            perm_req = self.database_cur.execute(
                "SELECT privilege_level FROM permissions WHERE id = (?) LIMIT 1", (val[0],))
            priv = perm_req.fetchone()
            if priv is None:
                priv = (0,)
                self.database_cur.execute("""BEGIN""")
                try:
                    self.database_cur.execute(
                        """INSERT INTO permissions VALUES(?, ?)""", (val[0], 0))
                    self.database.commit()
                except sqlite3.Error as ex:
                    print(
                        f"An error occurred: {ex}\nRolling back databases...")
                    print(traceback.format_exc())
                    self.database.rollback()
                    error_response = build_message_generic(
                        "error", "data-error", 'An error occurred')
                    self.message_handler.send_message(addr, error_response)
                    return False
            uuid_temp = UUID(bytes=val[0])
            client = Client(
                uuid_temp, val[1], datetime.now(), privilege_level=priv[0])
            login = self.client_handler.add_client(client)

            if login is False:
                client = self.client_handler.get_client(username)
                if client.addr[0] != addr[0]:
                    del client
                    error_response = build_message_generic(
                        "error", "already-connected", 'User is already logged in.')
                    self.message_handler.send_message(addr, error_response)
                    return False
            client.set_addr(addr)
            self.client_handler.update_client_ts(client.id)
            success_response = {
                "response": "success",
                "type": "login-success",
                "session": client.get_session(),
                "name": client.name,
                "id": str(client.id),
                "chunk-width": self.world_handler.chunk_width,
                "chunk-height": self.world_handler.chunk_height,
                "world-width": self.world_handler.width,
                "world-height": self.world_handler.height
            }
            self.message_handler.send_message(addr, success_response)
            return True
        else:
            error_response = build_message_generic(
                "error", "invalid-info", 'Password was invalid.')
            self.message_handler.send_message(addr, error_response)
            return False

    def register(self, data, addr) -> bool:
        """Registers a new user
        """
        if 'username' not in data or 'password' not in data:
            error_response = build_message_generic(
                "error", "missing-data", 'Required data is missing.')
            self.message_handler.send_message(addr, error_response)
            return False
        username = data['username']
        password = data['password']

        if (username.isspace() and username):
            error_response = build_message_generic(
                "error", "username-is-empty", f'{username} cannot be blank.')
            self.message_handler.send_message(addr, error_response)
            return False

        res = self.database_cur.execute(
            "SELECT EXISTS (SELECT 1 FROM users WHERE name = (?))", (username,))
        result = res.fetchone()

        if result is None or result[0] == 1:
            error_response = build_message_generic(
                "error", "username-in-use", f'{username} is already in use.')
            self.message_handler.send_message(addr, error_response)
            return False

        password = rsa.decrypt(base64.b64decode(password), self.privatekey)

        if (password.isspace() and password):
            error_response = build_message_generic(
                "error", "password-is-empty", f'{password} cannot be blank.')
            self.message_handler.send_message(addr, error_response)
            return False

        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt(10))

        self.database_cur.execute("""BEGIN""")
        try:
            uid = uuid4().bytes
            self.database_cur.execute(
                """INSERT INTO users VALUES(?, ?, ?)""", (uid, username, hashed_password))
            self.database_cur.execute(
                """INSERT INTO permissions VALUES(?, ?)""", (uid, 0))
            self.database.commit()
        except sqlite3.Error as ex:
            print(f"An error occurred: {ex}\nRolling back databases...")
            print(traceback.format_exc())
            self.database.rollback()
            error_response = build_message_generic(
                "error", "data-error", 'An error occurred')
            self.message_handler.send_message(addr, error_response)
            return False

        success_response = build_message_generic(
            "success", "register-success", f'User {username} was created successfully!')
        self.message_handler.send_message(addr, success_response)
        return True

    def end_session(self, data, addr):
        """ Ends a clients session
        """
        if 'session-id' not in data:
            error_response = build_message_generic(
                "error", "missing-data", "Required data is missing")
            self.message_handler.send_message(addr, error_response)
            return False
        session_id = data['session-id']

        try_remove = self.client_handler.remove_client_ses(session_id)

        if try_remove is True:
            response = build_message_generic(
                "success", "logout-success", "Successfully ended session")
            self.message_handler.send_message(addr, response)
            return True
        else:
            error_response = build_message_generic(
                "error", "user-not-connected", "Could not log out: User isn't connected.")
            self.message_handler.send_message(addr, error_response)
            return False

    def message(self, data, addr):
        """ Sends client chat messages to the message handler
        """
        if 'session-id' not in data or 'message' not in data:
            error_response = build_message_generic(
                "error", "missing-data", "Required data is missing")
            self.message_handler.send_message(addr, error_response)
            return False
        session_id = data['session-id']
        message = data['message']

        if not message.strip():
            return False

        client = self.client_handler.get_client_ses(session_id)
        if client is None:
            error_response = build_message_generic(
                "error", "incorrect-data", "Important data is incorrect")
            self.message_handler.send_message(addr, error_response)
            return False

        self.database_cur.execute("""BEGIN""")
        try:
            self.database_cur.execute(
                """INSERT INTO messages VALUES(?, ?, ?, ?)""",
                (uuid4().bytes, datetime.now(), message, client.id.bytes))
            self.database.commit()
        except sqlite3.Error as ex:
            print(f"An error occurred: {ex}\nRolling back databases...")
            print(traceback.format_exc())
            self.database.rollback()
            error_response = build_message_generic(
                "error", "data-error", 'An error occurred')
            self.message_handler.send_message(addr, error_response)
            return False

        message_json = {
            "response": "message",
            "origin": str(client.id),
            "message": message
        }
        self.client_handler.send_message_to_all(
            message_json, self.message_handler)
        return True

    def move(self, data, addr):
        """ Sends client movement to the World thread for handling
        """
        if 'session-id' not in data not in data:
            error_response = build_message_generic(
                "error", "missing-data", "Required data is missing")
            self.message_handler.send_message(addr, error_response)
            return False
        session_id = data['session-id']
        vel = [data['x'], data['y']]
        client = self.client_handler.get_client_ses(session_id)
        client.move(vel)
        return True

    def end_move(self, data, addr):
        """ Ends movment of a client
        """
        if 'session-id' not in data not in data:
            error_response = build_message_generic(
                "error", "missing-data", "Required data is missing")
            self.message_handler.send_message(addr, error_response)
            return False
        session_id = data['session-id']
        client = self.client_handler.get_client_ses(session_id)
        client.move([0, 0])
        return True

    def update_clients(self, data, addr):
        """ Requests the World thread to update a client
        """
        if 'session-id' not in data:
            error_response = build_message_generic(
                "error", "missing-data", "Required data is missing")
            self.message_handler.send_message(addr, error_response)
            return False

        session_id = data['session-id']
        client = self.client_handler.get_client_ses(session_id)
        with self.world_handler.lock:
            self.world_handler.full_update(client)
        return True

    def confirm(self, data, addr):
        """Confirms a packet
        """
        if 'packet-id' not in data:
            self.message_handler.send_message(addr, build_message_generic(
                "error", "invalid-packet-id", "Supplied packet id was invalid or missing."))
            return False
        packet_id = UUID(data["packet-id"])

        self.message_handler.confirm_message(packet_id)
        return True

    def ping(self, _data, _addr):
        """Ping
        """
        return False

    def sendkey(self, data, addr):
        """Sends the public key
        """
        data = {
            "response": "confirm-public",
            "public-key": self.p_key
        }
        self.message_handler.send_message(addr, data)
        return True

    def input_clbk(self, inp):
        """ Handles commands from the input thread
        """
        try:
            if not self.command_processor.parse_command(inp, self.server_client):
                print('Invalid Command. type `commands` for a list of commands.')
        except OSError as ex:
            self.close_server()
            print(ex)
            print(traceback.format_exc())

    def client_clbk(self, req, param: dict):
        """ Handles requests from the client handler thread
        """
        match req.lower():
            case 'relay-message':
                self.sock.sendto(param['json'], param['addr'])
            case 'kick':
                self.message_handler.send_message(param['addr'], build_message_generic(
                    'info', 'kicked', 'You have been kicked from the server.'))

    def process_websocket_message(self, message: str, addr: Union[str, tuple]):
        """ Handles requests passed from the websocketrelay
        """
        self.decode_json(message, addr)

    def stop_all_threads(self):
        """ Tells all threads to stop
        """
        try:
            self.client_handler.stop()
            if self.client_handler is not None:
                self.client_handler.join()
            self.message_handler.stop()
            self.world_handler.stop()
            self.keyboard.stop()
            if self.message_handler is not None:
                self.message_handler.join()
        except OSError as ex:
            print(ex)
            print(traceback.format_exc())

    def close_server(self):
        """Closes the server
        """
        try:
            self.running = False
            self.sock.sendto(b'{"request":"confirm"}',
                             ("127.0.0.1", self.port))
        except OSError as ex:
            print(ex)


if __name__ == '__main__':
    server.append(ServerThread("", 25555))
    try:
        if server[0] is not None:
            server[0].join()
    except KeyboardInterrupt:
        exit(0)
    sys.exit(0)
