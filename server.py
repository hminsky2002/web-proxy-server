import selectors
import socket
from http_parser import *
from collections import defaultdict
from dataclasses import dataclass
import re
from time import time
from typing import Optional
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(filename='server.log', encoding='utf-8', level=logging.DEBUG)

sel = selectors.DefaultSelector()

@dataclass
class CachedRequest:
    max_age: int
    response: bytes
    cached_at: float

server_cache = dict[str, CachedRequest]()

def parse_cache_control(cache_control_value: str) -> Optional[int]:
    if not cache_control_value:
        return None
    
    match = re.search(r'max-age=(\d+)', cache_control_value, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def extract_cache_control_from_response(response: bytes) -> Optional[int]:
    try:
        response_str = response.decode('utf-8', errors='ignore')
        lines = response_str.split('\r\n')
        
        for line in lines:
            if line.lower().startswith('cache-control:'):
                
                value = line.split(':', 1)[1].strip()
                
                return parse_cache_control(value)
            
    except Exception:
        pass
    return None

def accept(sock: socket.socket, mask, args):
    
    conn, addr = sock.accept()
    
    conn.setblocking(False)
    
    sel.register(conn, selectors.EVENT_READ, (receive, None))

def receive(conn: socket.socket, mask, addr):
    data = conn.recv(1000)
    if data:
        http_dict = parse_http_request(data)
        port = http_dict.host.port if http_dict.host.port != None else 80
        host = http_dict.host.host_name
        
        cache_key = http_dict.request_line
        
        if cache_key in server_cache:
            logger.debug('checking cache key', cache_key)
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
    else:
        sel.unregister(conn)
        conn.close()

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
    
    response = proxy_sock.recv(4096)
    
    if response:
        max_age = extract_cache_control_from_response(response)
        if max_age is not None:
            cached = CachedRequest(max_age, response, time())
            server_cache[cache_key] = cached
        
        client_conn.sendall(response)
    
    sel.unregister(proxy_sock)
    proxy_sock.close()
    sel.unregister(client_conn)
    client_conn.close()

sock = socket.socket()
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