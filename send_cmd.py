import socket

HOST = "127.0.0.1"
PORT = 5557

while True:
    cmd = input("> ").strip()
    if not cmd:
        continue
    if cmd in ("quit", "exit"):
        break

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall((cmd + "\n").encode("utf-8"))
        resp = s.recv(65536).decode("utf-8")
        print(resp)