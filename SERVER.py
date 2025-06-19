import socket
import threading
import os

SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5001
BUFFER_SIZE = 4096
STORAGE_DIR = "assets"

if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

def recv_line(sock):
    """Receive bytes from socket until newline (\n)"""
    data = b''
    while not data.endswith(b'\n'):
        part = sock.recv(1)
        if not part:
            break
        data += part
    return data.decode('utf-8').strip()

def handle_client(client_socket, address):
    try:
        print(f"[+] Connection from {address}")

        header = recv_line(client_socket)
        print(f"[+] Received header: {header}")

        if header.startswith("UPLOAD|"):
            parts = header.split('|')
            if len(parts) != 3:
                client_socket.send(b"INVALID")
                print("[!] Invalid UPLOAD header format")
                return

            _, filename, filesize_str = parts
            try:
                filesize = int(filesize_str)
            except ValueError:
                client_socket.send(b"INVALID")
                print("[!] Invalid filesize in header")
                return

            filepath = os.path.join(STORAGE_DIR, filename)

            client_socket.send(b"READY")
            print(f"[~] Receiving file '{filename}' ({filesize} bytes)...")

            with open(filepath, "wb") as f:
                remaining = filesize
                while remaining > 0:
                    chunk = client_socket.recv(min(BUFFER_SIZE, remaining))
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)

            if remaining == 0:
                print(f"[✓] File '{filename}' uploaded successfully.")
            else:
                print(f"[!] File '{filename}' upload incomplete.")

        elif header.startswith("DOWNLOAD|"):
            parts = header.split('|')
            if len(parts) != 2:
                client_socket.send(b"INVALID")
                print("[!] Invalid DOWNLOAD header format")
                return

            _, filename = parts
            filepath = os.path.join(STORAGE_DIR, filename)
            if not os.path.exists(filepath):
                client_socket.send(b"NOTFOUND\n")
                print(f"[!] File '{filename}' not found.")
                return

            filesize = os.path.getsize(filepath)
            client_socket.send(f"SIZE|{filesize}\n".encode('utf-8'))
            print(f"[~] Sending file '{filename}' ({filesize} bytes)...")

            with open(filepath, "rb") as f:
                while chunk := f.read(BUFFER_SIZE):
                    client_socket.sendall(chunk)

            print(f"[✓] File '{filename}' sent successfully.")

        else:
            print(f"[!] Unknown command: {header}")
            client_socket.send(b"INVALID")

    except Exception as e:
        print(f"[!] Exception handling client {address}: {e}")

    finally:
        client_socket.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((SERVER_HOST, SERVER_PORT))
    server.listen(5)
    print(f"[+] Server listening on {SERVER_HOST}:{SERVER_PORT}...")

    while True:
        client_sock, addr = server.accept()
        threading.Thread(target=handle_client, args=(client_sock, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()
