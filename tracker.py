import socket #INTERNET MAGNAMENT THROUGH TCP AND UDP
import threading #TAKE CARE OF MULTITHREADING
import sqlite3 #FOR THE EXTENSION DATABASE
import pickle #serialize AND DESERIALIZE
import traceback #PROVIDE DETAIL INFORMATION WHEN EXCEPTAION OCCUR

from command import *
from support import *
from torrent import *

HOST_NAME = socket.gethostname()
HOST_IP = socket.gethostbyname(HOST_NAME)
PORT = 1606

class Tracker:
    # @__init__
    # This part create a constructor of the class Tracker, 
    # Connect itself to the sqlite3 before execute
    # Using the IPv4 and TCP
    # put it in the listening queue
    # Create the Table that store all the information into sqlite
    def __init__(self, db_path='tracker.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()
        
        self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_socket.bind((HOST_IP, PORT))
        self.tracker_socket.listen(QUEUE_SIZE)
        self.sqlite3_create()
        self.files: Set[str] = set() #The infomation of files which register on tracker
        self.peers_with_file: Dict[str, Set[int]] = {} #Check which peer have the file
        
    # @Create a table with all information of peer
    # id
    # username
    # password 
    # ip 
    # port 
    # status
    def sqlite3_create(self):
        with self.lock:
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                username TEXT UNIQUE,
                                password TEXT,
                                ip TEXT,
                                port INTEGER,
                                status INTEGER
                                )''')
            self.conn.commit()
        
    # @connect_from_peers
    # handle when peer want to connect to the server
    # and excute function base on the command
    def connect_from_peers(self, client_socket, addr):
        print(f"Initiating connection handling for {addr}")
        while True:
            try:
                print(f"Awaiting incoming data from {addr}")
                data = receiveMess(client_socket)
                if data is None:
                    print(f"Client {addr} closed connection")
                    break
                print(f"Received {len(data)} bytes from {addr}")
                info = pickle.loads(data)
                print(f"Message is receieved from {addr}: {info['type']}")
                if info['type'] == REGISTER:
                    self.sign_up(client_socket, info)
                # elif info['type'] == LOGIN:
                #     self.loginService(client_socket, info)
                # elif info['type'] == REGISTER_FILE:
                #     peer_id = info['peer_id']
                #     self.uploadFile(client_socket, info, peer_id)
                # elif info['type'] == REQUEST_FILE:
                #     self.peerHoldFileService(client_socket, info['file_name'])
                # elif info['type'] == GET_LIST_FILES_TO_DOWNLOAD:
                #     self.showFileAvailable(client_socket)
                # elif info['type'] == LOGOUT:
                #     self.logoutService(client_socket, info)
              
                
                # ... xử lý các loại tin nhắn khác ...
            except Exception as e:
                print(f"Failed in handling peer {addr}: {e}")
                traceback.print_exc()
                break
        print(f"Close the connection for {addr}")
        client_socket.close()
    
    def sign_up(self, client_socket, info):
        user, passwd, ip, port = info['username'], info['password'], info['ip'], info['port']
        print(f"Registering peer: {user}")
        try:
            record = self.getAccountByUsername(user)
            if record:
                print(f"Peer {user} already exists")
                self.sendMess(client_socket, {'type': REGISTER_FAILED, 'message': 'This account has already exist'})
            else:
                self.insertUser(user, passwd, ip, port)
                peer_id = self.getPeerId(user)
                print(f"Peer {user} registered successfully with ID {peer_id}")
                    
                self.sendMess(client_socket, {'type': REGISTER_SUCCESSFUL, 'message': 'Account created successfully', 'peer_id': peer_id})
        except Exception as e:
            print(f"Issue occurred during registration: {e}")
            traceback.print_exc()
            self.sendMess(client_socket, {'type': REGISTER_FAILED, 'message': 'Internal server error'})    
    
    # @run
    # Run the grogram duh
    def run(self):
            print(f"The tracker server is listening on {HOST_IP}:{PORT}")
            while True:
                try:
                    client_socket, addr = self.tracker_socket.accept()
                    print(f"There is a new connection from {addr}")
                    client_thread = threading.Thread(target=self.connect_from_peers, args=(client_socket, addr))
                    client_thread.start()
                except Exception as e:
                    print(f"An error accepting connection: {e}")
                    traceback.print_exc()
                except KeyboardInterrupt:
                    print("Program interrupted by peer.")
                    break

if __name__ == '__main__':
    tracker = Tracker()
    tracker.run()