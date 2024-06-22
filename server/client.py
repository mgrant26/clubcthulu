"""Provides socket operations and related functions"""
import socket
import json
import base64
import rsa

IP = "127.0.0.1"
PORT = 25555
MESSAGE =  json.dumps({
    "request": "obtain-public"
}).encode('utf-8')

LOGIN_REQUEST = 0

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

#Request login
sock.sendto(MESSAGE, (IP, PORT))

sock.settimeout(5)
data, addr = sock.recvfrom(1024)
if data:
    dedata = json.loads(data.decode('utf-8'))
    mess = json.dumps({
        "request": "confirm",
        "packet-id": dedata['packet-id']
    }).encode('utf-8')
    sock.sendto(mess, (IP, PORT))

dedata = data.decode('utf-8')
jsonl = json.loads(dedata)
keystr = jsonl['public-key']

key = rsa.PublicKey.load_pkcs1(keystr.encode('utf-8'))
pc = rsa.encrypt('Password'.encode('utf-8'), key)

MESSAGE2 = json.dumps({
    "request": "register",
    "username": "dave",
    "password": base64.b64encode(pc).decode('utf-8')
}).encode('utf-8')
sock.sendto(MESSAGE2, (IP, PORT))

data, addr = sock.recvfrom(1024)
if data:
    dedata = json.loads(data.decode('utf-8'))
    mess = json.dumps({
        "request": "confirm",
        "packet-id": dedata['packet-id']
    }).encode('utf-8')
    sock.sendto(mess, (IP, PORT))
    dedata = data.decode('utf-8')
    print(dedata)

MESSAGE3 = json.dumps({
    "request": "init-session",
    "username": "dave",
    "password": base64.b64encode(pc).decode('utf-8')
}).encode('utf-8')
sock.sendto(MESSAGE3, (IP, PORT))

data, addr = sock.recvfrom(1024)
if data:
    dedata = json.loads(data.decode('utf-8'))
    mess = json.dumps({
        "request": "confirm",
        "packet-id": dedata['packet-id']
    }).encode('utf-8')
    sock.sendto(mess, (IP, PORT))
    dedata = json.loads(data.decode('utf-8'))
    print(dedata)
    sessionid = dedata['session']

MESSAGE4 = json.dumps({
    "request": "end-session",
    "session-id": sessionid
}).encode('utf-8')
sock.sendto(MESSAGE4, (IP, PORT))

data, addr = sock.recvfrom(1024)
if data:
    dedata = json.loads(data.decode('utf-8'))
    mess = json.dumps({
        "request": "confirm",
        "packet-id": dedata['packet-id']
    }).encode('utf-8')
    sock.sendto(mess, (IP, PORT))
    dedata = json.loads(data.decode('utf-8'))
    print(dedata)
