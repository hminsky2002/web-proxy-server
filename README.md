# HTTP Web Proxy Server

An HTTP web proxy server implementation using low-level socket interfaces in Python. The server uses non-blocking sockets with the `selectors` module for event-driven I/O, implements HTTP request parsing and forwarding, and includes response caching with `Cache-Control: max-age`. It has a fairly large initial read buffer for connections, but if it detects a content-length header it will read until it reaches the end of the content-length. It does not support chunked http responses. Logs are written to server.log.

The main proxy logic is in [server.py](server.py), with HTTP parsing utilities (including `parse_http_request()`, `generate_proxy_http_request()`, and header extraction functions) in [http_parser.py](http_parser.py). Start the server with `python server.py [port]` (defaults to port 1234), and test it with the simple client socket script, [client.py](client.py) using `python client.py <proxy_port> <target_host>`. 

You can run it with a a Python 3 virtual environment (`python3 -m venv venv && source venv/bin/activate`), though the server uses only standard library modules so it could run on system Python.
