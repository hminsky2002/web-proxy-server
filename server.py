import selectors
import socket
from http_parser import *
from dataclasses import dataclass
from time import time
import logging


receive_default_size = 8000

logger = logging.getLogger(__name__)
logging.basicConfig(filename='server.log', encoding='utf-8', level=logging.DEBUG)

sel = selectors.DefaultSelector()

@dataclass
class CachedRequest:
    max_age: int
    response: bytes
    cached_at: float

server_cache = dict[str, CachedRequest]()

def accept(sock: socket.socket, mask, args):
    
    conn, addr = sock.accept()
    
    conn.setblocking(False)
    
    sel.register(conn, selectors.EVENT_READ, (receive_client, None))

def receive(conn: socket.socket) -> bytes | None:
    data = conn.recv(receive_default_size)
    if not data:
        return None
    header_end = data.find(b'\r\n\r\n')
    if header_end == -1:
        logger.error("Headers are too large, please don't sent in this many large headers :'( ")
        return None
    
    headers_bytes = data[:header_end]
    content_length = extract_header_from_response('content-length', headers_bytes, parse_content_length_header)
    
    body_start = header_end + 4  
    body_received = len(data) - body_start
    
    if content_length and body_received < content_length:
        remaining = content_length - body_received
        logger.debug(f'Reading {remaining} more bytes')
        
        conn.setblocking(True)  
        conn.settimeout(10.0)  
        
        try:
            while remaining > 0:
                chunk = conn.recv(min(remaining, receive_default_size))
                if not chunk:
                    logger.error("Connection closed before receiving full body")
                    return None
                data += chunk
                remaining -= len(chunk)
        except socket.timeout:
            logger.error("Timeout reading request body")
            return None
        finally:
            conn.setblocking(False) 
    
    return data


def receive_client(conn: socket.socket, mask, addr):
    
    data = receive(conn)
    
    if not data:
        sel.unregister(conn)
        conn.close()
        return
    
    msg = data.decode()
    logger.debug(f'Received data from client: {msg}')
    
    http_dict = parse_http_request(data)
    port = http_dict.host.port if http_dict.host.port != None else 80
    host = http_dict.host.host_name
    
    cache_key = http_dict.request_line
    
    if cache_key in server_cache:
        logger.debug('Checking cache key', cache_key)
        cached = server_cache[cache_key]
        age = time() - cached.cached_at
        if age < cached.max_age:
            conn.sendall(cached.response)
            sel.unregister(conn)
            conn.close()
            return
        else:
            del server_cache[cache_key]
               
    proxy_sock = socket.socket()
    proxy_sock.setblocking(False)
    
    if isinstance(port, str):
        port = int(port)
        
    proxy_sock.connect_ex((host, port))
    sel.register(proxy_sock, selectors.EVENT_WRITE,
                    (send_proxy_connection_req, (http_dict, conn, cache_key)))


def send_proxy_connection_req(proxy_sock: socket.socket, mask, args):
    http_dict, client_conn, cache_key = args
    
    err = proxy_sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
    
    if err == 0:
        
        sel.modify(proxy_sock, selectors.EVENT_WRITE,
                   (send_proxy_data, (http_dict, client_conn, cache_key)))
        
    else:
        
        sel.unregister(proxy_sock)
        proxy_sock.close()
        sel.unregister(client_conn)
        client_conn.close()

def send_proxy_data(proxy_sock: socket.socket, mask, args):
    http_dict, client_conn, cache_key = args
    
    message = generate_proxy_http_request(http_dict)
    
    logger.debug('proxy message being sent:', message.decode())
    
    proxy_sock.sendall(message)
    
    sel.modify(proxy_sock, selectors.EVENT_READ,
               (receive_proxy_response, (client_conn, cache_key)))

def receive_proxy_response(proxy_sock: socket.socket, mask, args):
    client_conn, cache_key = args
    
    response = receive(proxy_sock)
    
    if response:
        max_age = extract_header_from_response('cache-control',response, parse_cache_control)
        if max_age is not None:
            cached = CachedRequest(max_age, response, time())
            server_cache[cache_key] = cached
        
        client_conn.sendall(response)
    
    sel.unregister(proxy_sock)
    proxy_sock.close()
    sel.unregister(client_conn)
    client_conn.close()
    

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('localhost', 1234))
sock.listen(100)
sock.setblocking(False)
sel.register(sock, selectors.EVENT_READ, (accept, None))

while True:
    events = sel.select()
    for key, mask in events:
        callback = key.data[0]
        args = key.data[1]
        callback(key.fileobj, mask, args)