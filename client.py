import socket
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <proxy_port> [target_host]")
        sys.exit(1)

    proxy_port = int(sys.argv[1])
    target_host = sys.argv[2] if len(sys.argv) > 2 else "example.com"

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect(('localhost', proxy_port))

    request = (
        f"GET / HTTP/1.1\r\n"
        f"Host: {target_host}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    )

    client_sock.sendall(request.encode())
    response = client_sock.recv(4096)

    print(f"Received {len(response)} bytes from proxy")
    print(response.decode('utf-8', errors='ignore'))

    client_sock.close()

if __name__ == '__main__':
    main()
