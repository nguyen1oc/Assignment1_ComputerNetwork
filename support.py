import struct
import pickle
import bencodepy
import maskpass
import hashlib
def receiveMess(sock):
    # Nhận kích thước của tin nhắn đầu tiên
    firstMessLen =  receiveAll(sock, 4)
    if not firstMessLen:
        return None
    msgLen = struct.unpack('>I', firstMessLen)[0]
     # H nhận dữ liệu tin nhắn
    return  receiveAll(sock, msgLen)

def  receiveAll(sock, n):
  # nhận n byte hoặc trả về None nếu EOF hit
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data