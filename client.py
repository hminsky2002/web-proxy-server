import socket

get_request = b'''
POST /users HTTP/1.1
Host: example.com
Content-Type: application/x-www-form-urlencoded
Content-Length: 49

name=FirstName+LastName&email=bsmth%40example.com
'''



HOST = ''      
PORT = 50007              
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    s.sendall(get_request)
    data = s.recv(1024)
print('Received', repr(data))