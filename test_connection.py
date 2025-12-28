#!/usr/bin/env python3
import socket
import json

# Connect
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(5)
sock.connect(("127.0.0.1", 1776))

print("Connected!")

# Read welcome message (S0001)
welcome = b''
while True:
    chunk = sock.recv(4096)
    print(f"Received chunk: {chunk}")
    if not chunk:
        break
    welcome += chunk
    if b'\n' in welcome:
        welcome = welcome.split(b'\n')[0]
        break

print(f"Welcome: {welcome.decode('utf-8')}")

# Send auth
auth_cmd = json.dumps({"username": "root", "password": "root", "database": "primary"})
print(f"Sending auth: {auth_cmd}")
sock.sendall(auth_cmd.encode('utf-8') + b'\x04')

# Read auth response
auth_response = b''
while True:
    chunk = sock.recv(4096)
    print(f"Received auth chunk: {chunk}")
    if not chunk:
        break
    auth_response += chunk
    if b'\n' in auth_response:
        auth_response = auth_response.split(b'\n')[0]
        break

print(f"Auth response: {auth_response.decode('utf-8')}")

# Send SHOW DATABASES
print("Sending: SHOW DATABASES;")
sock.sendall(b'SHOW DATABASES;\x04')

# Read response
response = b''
while True:
    chunk = sock.recv(4096)
    print(f"Received response chunk: {chunk}")
    if not chunk:
        break
    response += chunk
    if b'\n' in response:
        response = response.split(b'\n')[0]
        break

print(f"Response: {response.decode('utf-8')}")

sock.close()
