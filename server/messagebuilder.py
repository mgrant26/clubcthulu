"""Message handling classes
"""
import json
import traceback
import time
import asyncio
from uuid import uuid4
from threading import Thread, RLock
from datetime import datetime, timedelta
from utils import Timer


class Message:
    """Message container class
    """

    def __init__(self, message, addr, retry, retry_int):
        self.message = message
        self.addr = addr
        self.retry = retry
        self.retry_int = retry_int


def build_message_generic(name, msg_type, message):
    """Builds a generic response
    """
    response = {
        "response": name,
        "type": msg_type,
        "message": message,
    }
    return response


class MessageRelay(Thread):
    """MessageRelay class
    """
    max_retries = 1
    retry_interval = timedelta(milliseconds=500)
    waiting = {}
    to_remove = []
    lock = RLock()
    running = True

    def __init__(self, sock, websocket_relay = None, clbk=None,  name='MessageThread'):
        super(MessageRelay, self).__init__(name=name)
        self.clbk = clbk
        self.daemon = True
        self.websocket_relay = websocket_relay
        self.sock = sock.dup()
        self.timer = Timer()
        self.delta = 0
        self.start()

    def run(self):
        print("Starting Message Handler...")
        while self.running:
            try:
                self.delta = self.timer.get_delta()
                if len(self.waiting) > 0:
                    self.update(self.delta)
            except IOError as e:
                print(f'Error in Message Handler: {e}')
                print(traceback.format_exc())
        self.stop()
        self.sock.close()

    def get_waiting(self):
        """Returns the messages waiting to be sent
        """
        with self.lock:
            return self.waiting.copy()

    def send_message(self, addr, message, retries=max_retries):
        """ Adds a message to the delivery queue
        """
        with self.lock:
            packet_id = uuid4()
            message['packet-id'] = str(packet_id)
            message['timestamp'] = datetime.now().timestamp()
            to_send = json.dumps(message)
            self.waiting[packet_id] = Message(
                to_send, addr, retries, self.retry_interval)
            return message

    def update(self, delta):
        """ Empties the queue
        """
        with self.lock:
            for key in self.waiting.items():
                if key[1].retry_int >= self.retry_interval:
                    self.resend_message_no_lock(key[0])
                key[1].retry_int = key[1].retry_int + delta
            for mid in self.to_remove:
                self.waiting.pop(mid, None)
            self.to_remove.clear()
            time.sleep(0)

    def resend_message_no_lock(self, mid) -> bool:
        """Attempts to resend a message without using a lock
        """
        if mid not in self.waiting:
            return False
        if self.waiting.get(mid).retry < 1 or not self.waiting.get(mid).addr[0]:
            self.to_remove.append(mid)
            return False
        self.waiting.get(mid).retry_int = timedelta(seconds=0)
        self.waiting.get(mid).retry -= 1
        if self.websocket_relay is not None and self.waiting.get(mid).addr in self.websocket_relay.clients:
            msg = self.waiting.get(mid)
            asyncio.run(self.websocket_relay.clients.get(msg.addr).send(msg.message.encode(
                'utf-8')))
        else:
            self.sock.sendto(self.waiting[mid].message.encode(
                'utf-8'), self.waiting[mid].addr)

    @staticmethod
    def send_message_async(sock, message):
        """Directly sends a message
        """
        message = message[0]
        if message[1] is None:
            return None
        if message[1].retry < 1:
            return message[0], None
        message[1].retry_int = timedelta(seconds=0)
        message[1].retry -= 1
        try:
            sock.sendto(message[1].message.encode('utf-8'), message[1].addr)
        except TimeoutError:
            pass
        if message[1].retry == 0:
            return message[0], None
        return message

    def send_message_clbk(self, result):
        """ Callback function for message sending
        """
        result = result[0]
        if len(result) > 1 and result[1] is not None:
            print("help")
            self.waiting[result[0]] = result[1]
        else:
            print(result)
            self.waiting.pop(result[0], None)
            print(self.waiting)

    def resend_message(self, mid) -> bool:
        """ Attempts to resend a message
        """
        with self.lock:
            self.resend_message_no_lock(mid)

    def confirm_message(self, mid) -> bool:
        """ Attempts to confirm a message
        """
        with self.lock:
            if mid not in self.waiting:
                return False
            self.to_remove.append(mid)
            return True

    def stop(self):
        """Stops this thread
        """
        self.running = False
