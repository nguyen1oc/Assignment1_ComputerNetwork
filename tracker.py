import socket #INTERNET MAGNAMENT THROUGH TCP AND UDP
import threading #TAKE CARE OF MULTITHREADING
import sqlite3 #FOR THE EXTENSION DATABASE
import pickle #serialize AND DESERIALIZE
import traceback #PROVIDE DETAIL INFORMATION WHEN EXCEPTAION OCCUR
import os

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
        self.peers_have_files: Dict[str, Set[int]] = {} #Check which peer have the file

    # @Create a table with all information of peer
    # id
    # username
    # password 
    # ip 
    # port 
    # status
    def sqlite3_create(self):
        with self.lock:
            # Create table if doesnot exist at first
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    username TEXT UNIQUE,
                                    password TEXT,
                                    ip TEXT,
                                    port INTEGER,
                                    status INTEGER
                                    )''')
            self.conn.commit()
            
            # Reset AUTOINCREMENT after delete all the data
            self.cursor.execute("DELETE FROM users")  
            self.cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'users'") 
            self.conn.commit()
        
    # @connect_from_peers
    # Handles incoming connections from peers
    # Listens for messages from the peer and processes them based on the message type
    # If an error occurs during message processing or connection, it handles the exception and closes the connection for the peer
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
                elif info['type'] == LOGIN:
                    self.login(client_socket, info)
                elif info['type'] == UPLOAD_FILE:
                     peer_id = info['peer_id']
                     self.upload(client_socket, info, peer_id)
                elif info['type'] == REQUEST_FILE:
                     self.peer_hold_files(client_socket, info['file_name'])
                elif info['type'] == GET_LIST_FILES_TO_DOWNLOAD:
                     self.show_files(client_socket)
                elif info['type'] == LOGOUT:
                     self.logout(client_socket, info)
              
            except Exception as e:
                print(f"Issue occured when connected from peers at {addr}: {e}")
                traceback.print_exc()
                break
        print(f"Close the connection for {addr}")
        client_socket.close()
    
    # @sign_up
    # Handles the registration process for a new peer
    # Receives the user details (user name, password, IP, and port) from the client
    # Checks if the user already exists by querying the user database
    # If the user exists, sends a REGISTER_FAILED response indicating the account already exists
    # If the user doesn't exist, inserts the user into the database and generates a unique peer ID
    # If an error occurs during registration, catches the exception and sends a REGISTER_FAILED response with an error message
    def sign_up(self, client_socket, info):
        user, pwd, ip, port = info['user_name'], info['password'], info['ip'], info['port']
        print(f"Registering peer: {user}")
        try:
            tmp = self.get_user(user)
            if tmp:
                print(f"Peer {user} already exists")
                self.send_mess(client_socket, {'type': REGISTER_FAILED, 'message': 'This account has already exist'})
            else:
                self.insert_user(user, pwd, ip, port)
                peer_id = self.get_userId(user)
                print(f"Peer {user} registered successfully with ID {peer_id}")
                    
                self.send_mess(client_socket, {'type': REGISTER_SUCCESSFUL, 'message': 'Account created successfully', 'peer_id': peer_id})
        except Exception as e:
            print(f"Issue occurred during registration: {e}")
            traceback.print_exc()
            self.send_mess(client_socket, {'type': REGISTER_FAILED, 'message': 'Internal server error'})    
    
    
    # @login
    # Handles the login process for a peer
    # Receives the user details (user name, password, IP, and port) from the client
    # Checks if the user exists in the database
    # If the user exists, compares the provided password with the stored password
    # If the password is correct, generates the peer ID and sends a LOGIN_SUCCESSFUL response with the peer ID
    # If the password is incorrect or the user does not exist, sends a LOGIN_FAILED response with an error message
    # Updates the peer's status (IP and port) after a successful login
    # If an error occurs during login, catches the exception and sends a LOGIN_FAILED response with an error message
    def login(self, client_socket, info):
        user, pwd, ip, port = info['user_name'], info['password'], info['ip'], info['port']
        print(f"User logging: {user}")
        try:
            tmp = self.get_user(user)
            if tmp:
                if tmp[2] == pwd:
                    peer_id = self.get_userId(user)
                    self.send_mess(client_socket, {'type': LOGIN_SUCCESSFUL, 'message': 'Login successful', 'peer_id': peer_id})
                    self.update_status(user, ip, port)
                else:
                    self.send_mess(client_socket, {'type': LOGIN_FAILED, 'message': 'Incorrect password'})
            else:
                self.send_mess(client_socket, {'type': LOGIN_FAILED, 'message': 'Incorrect password'})
        except Exception as e:
            print(f"Issue occured when login: {e}")
            traceback.print_exc()
            self.send_mess(client_socket, {'type': LOGIN_FAILED, 'message': 'Internal server error'})
    
    # @upload
    # Handles the file upload process when a peer uploads a file to the server
    # Receives metadata (metainfo) about the file from the client
    # Adds the file name to the list of files managed by the tracker
    # Checks if the file is already present in 'peers_have_files', if not, creates a new entry for it
    # Adds the peer's ID to the list of peers who hold the file
    # Generates a magnet link for the uploaded file using its metadata and the tracker's address
    # Creates the upload directory if it doesn't exist
    # Creates and saves a .torrent file containing the file metadata in the 'repository_tracker' directory
    # Prints all the uploaded files and the associated peer IDs for each file
    # Sends a response to the client confirming the file upload completion and provides the magnet link
    def upload(self, client_socket, info, peer_id):
        metain4 = info['metainfo']
        print(f"Uploading {metain4['file_name']}....")
        self.files.add(metain4['file_name'])
        file_name = metain4['file_name']
        if file_name not in self.peers_have_files:
            self.peers_have_files[file_name] = set()
        
        self.peers_have_files[file_name].add(peer_id)
        magnet_link = magnet_Link(metain4, HOST_IP, PORT)
        
        upload_dir = 'repository_tracker'
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
    
        if not os.path.exists('repository_tracker' + metain4['file_name'] + '.torrent'):
            with open(os.path.join('repository_tracker', f"{metain4['file_name']}.torrent"), 'wb') as f:
                pickle.dump(metain4, f)
        print('All files have been uploaded:')
        for file in self.files:
            print(file)
                
        print('File name with peer_id:')
        for file in self.peers_have_files:
            print(file, self.peers_have_files[file])
                
        self.send_mess(client_socket, {
            'type': UPLOAD_FILE_COMPLETE,
            'message': 'File uploaded successfully',
            'magnet_link': magnet_link
        })
        
        
    # @peer_hold_files
    # Handles the process when a peer requests a list of peers holding a specific file
    # Retrieves the list of peer IDs who have the requested file from 'peers_have_files'
    # Looks up the IP and port for each peer using their peer ID
    # Sends a message back to the client with the list of peers holding the file
    # If no peers are found, sends a failure message indicating that no peers are currently online
    # Loads the .torrent file corresponding to the requested file and sends its metadata to the client
    def peer_hold_files(self, client_socket, file_name: str):
        list_peers = self.peers_have_files[file_name]
        list_ip_port = []
        for peer_id in list_peers:
            results = self.get_Ip_and_Port(peer_id)
            if results:
                list_ip_port.append(results)
                
        if not len(list_ip_port):
            self.send_mess(client_socket, {'type': SHOW_PEER_HOLD_FILE_FAILED, 'message': 'No peers that hold this file are currently online'})
            return
        
        
        with open(os.path.join('repository_tracker', f"{file_name}.torrent"), 'rb') as f:
            metainfo = pickle.load(f)
        
        self.send_mess(client_socket, {'type': SHOW_PEER_HOLD_FILE, 
                                     'metainfo': metainfo, 
                                    'ip_port_list': list_ip_port})
        
    def logout(self, client_socket, info):
        peer_id = info['peer_id']
        self.update_status(peer_id, 0)
        record = self.get_userOnline()
        print('Online users:')
        for user in record:
            print(user[1])
        self.send_mess(client_socket, {'type': LOGOUT_SUCCESSFUL, 'message': 'Logout successful'})
    
    def show_files(self, client_socket):
        self.send_mess(client_socket, {'type': GET_LIST_FILES_TO_DOWNLOAD, 'files': list(self.files)})
        
    #WORKING WITH DATABASE
    def get_user(self, user):
        self.cursor.execute("SELECT * FROM users WHERE username = ?", (user,))
        return self.cursor.fetchone()
    
    def get_userId(self, user):
        self.cursor.execute("SELECT id FROM users WHERE username = ?", (user,))
        return self.cursor.fetchone()[0]
    
    def insert_user(self, user, passwd, ip, port):
        with self.lock:
            self.cursor.execute("INSERT INTO users (username, password, ip, port, status) VALUES (?, ?, ?, ?, 0)", 
                                (user, passwd, ip, port))
            self.conn.commit()
        
    def update_status(self, user, ip, port):
        with self.lock:
            self.cursor.execute("UPDATE users SET  ip = ?, port = ?, status = 1 WHERE username = ?", (ip, port, user))
            self.conn.commit()
            
    def get_userOnline(self):
        with self.lock:
            self.cursor.execute("SELECT * FROM users WHERE status = 1")
        return self.cursor.fetchall()
    
    def get_Ip_and_Port(self, peer_id):
        self.cursor.execute("SELECT ip, port FROM users WHERE id = ? AND status = 1", (peer_id,))
        return self.cursor.fetchone()
    
    
    # @sendMess
    # Send messsage    
    def send_mess(self, client_socket, msg):
        try:
            sendMess(client_socket, msg)
            print(f"Sent message: {msg['type']}")
        except Exception as e:
            print(f"Error sending message: {e}")
            traceback.print_exc()
        
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