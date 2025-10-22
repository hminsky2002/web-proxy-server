from collections import defaultdict

crlf = '\r\n'

def parse_host_header(header: str) -> dict | None:
    
    if header == " " or not header:
        return None 
    
    host_dict = {}
    
    port_idx = header.find(':')
    if port_idx > 0:
        host_dict['port'] = header[port_idx:]
        host_dict['host_name'] = header[0:port_idx]
    else:
        host_dict['port'] = None
        host_dict['host_name'] = header
    
    return host_dict
       

def parse_http_request(data: bytes) -> dict:
    
    output_dict = {}
    
    parsed_data = data.decode("utf-8").split(crlf)
    
    request_line = parsed_data[0]
    
    output_dict['request_line'] = request_line
    
    headers = parsed_data[1:-2]
    
    header_mappings = defaultdict(str)
    
    prev_header = None
    
    for s in headers:
        if s[0] == " ":
            header_mappings[prev_header] += s   
            continue
        else:
            a = s.split(":") 
            header_mappings[a[0].strip()] = a[1].strip()
            prev_header = a[0]
    
    output_dict['headers'] = header_mappings
    
    if output_dict['headers']['Host']:
        output_dict['host'] = parse_host_header(output_dict['headers']['Host'])
    
    body = parsed_data[-1]
    
    output_dict['body'] = body
    
    return output_dict


        
        
    