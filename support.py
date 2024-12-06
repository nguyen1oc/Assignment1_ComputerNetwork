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

def receiveAll(sock, n):
  # nhận n byte hoặc trả về None nếu EOF hit
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def enter_Pasword():
    while True:
        pwd = maskpass.askpass(prompt="Enter your password: ", mask="*")
        verify = maskpass.askpass(prompt="Verify the password: ", mask="*")

        if pwd == verify:
            print("Password accepted.")
            return pwd
        else:
            print("Password unaccept")
            

def sendMess(sock, msg):
    msg = pickle.dumps(msg)
    sock.sendall(struct.pack('>I', len(msg)) + msg)
    
def magnet_Link(metain4, HOST, PORT):
    info_hash = bencodepy.encode(metain4).hex()
    file_name = metain4['file_name']
    file_size = metain4['file_size']
            
    magnet_link = f"magnet:?xt=urn:btih:{info_hash}&dn={file_name}&xl={file_size}"
        
    # Thêm tracker URL vào magnet link
    tracker_url = f"http://{HOST}:{PORT}/announce"
    magnet_link += f"&tr={tracker_url}" 
    
    return magnet_link


def sha1_hash(data):
    sha1 = hashlib.sha1()
    sha1.update(data)
    return sha1.hexdigest()


def file_into_pieces(path,piece_size):
    pieces = []
    with open(path, 'rb') as f:
        while True:
            piece = f.read(piece_size)
            if not piece:
                break
            pieces.append(sha1_hash(piece))
            
    return pieces

def send_piece(path, piece_size, index):
    pieces = []
    with open(path, 'rb') as f:
        idx = 0
        while True:
            piece = f.read(piece_size)
            if not piece:
                break
            temp = {'piece': piece, 'id': idx}
            pieces.append(temp)
            idx += 1
    pieces = [piece for piece in pieces if piece['id'] in index]
    return pieces