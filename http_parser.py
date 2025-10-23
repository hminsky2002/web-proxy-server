from dataclasses import dataclass
from typing import Optional

CRLF = '\r\n'

@dataclass
class HostInfo:
    host_name: str
    port: Optional[str] = None

@dataclass
class HttpRequest:
    request_line: str
    headers: dict[str, str]
    body: str
    host: HostInfo

def parse_host_header(header: str) -> Optional[HostInfo]:
    if header == " " or not header:
        return None
    
    port_idx = header.find(':')
    if port_idx > 0:
        return HostInfo(
            host_name=header[0:port_idx].strip(),
            port=header[port_idx+1:].strip()
        )
    else:
        return HostInfo(host_name=header.strip())

def parse_http_request(data: bytes) -> HttpRequest:
    parsed_data = data.decode("utf-8").split(CRLF)
    request_line = parsed_data[0]
    headers_raw = parsed_data[1:-2]
    
    header_mappings: dict[str, str] = {}
    prev_header: Optional[str] = None
    
    for line in headers_raw:
        if line and line[0] == " ":
            if prev_header:
                header_mappings[prev_header] += line
        else:
            colon_idx = line.find(":")
            if colon_idx > 0:
                header = line[0:colon_idx].strip()
                value = line[colon_idx+1:].strip()
                header_mappings[header] = value
                prev_header = header
    
    host_info = None
    if 'Host' in header_mappings:
        host_info = parse_host_header(header_mappings['Host'])
    else:
        raise ValueError("No Host Specified")
    
    if host_info == None:
        raise ValueError("No Host Specified")
    
    body = parsed_data[-1]
    
    return HttpRequest(
        request_line=request_line,
        headers=header_mappings,
        body=body,
        host=host_info
    )

def generate_proxy_http_request(request: HttpRequest) -> bytes:
    headers = request.headers.copy()
    
    if request.host:
        port_suffix = f':{request.host.port}' if request.host.port else ''
        headers['X-Forwarded-For'] = f'{request.host.host_name}{port_suffix}'
    
    headers_str = ''.join([f'{key}: {value}{CRLF}' for key, value in headers.items()])
    proxy_request = f'{request.request_line}{CRLF}{headers_str}{CRLF}{request.body}'
    
    return proxy_request.encode('utf-8')