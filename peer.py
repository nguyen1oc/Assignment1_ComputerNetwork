import socket
import threading
import sqlite3
import time
import json #JavaScript Object Notation convert to jason type
import os
import hashlib
import maskpass #using for hide the password
import pickle

from command import *
from torrent import *
from support import *


SERVER_NAME = socket.gethostname()
SERVER_IP = socket.gethostbyname(SERVER_NAME)
PORT = 1606

class Peer:
    # @__init__
    # Constructor of Peer
    # Create its self ip and port and the connect with other peers and tracker
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.peer_tracker_socket = None 
        self.peer_peers_socket = None
        
        self.user_name = None
        self.peer_id = None
        
        self.files: Dict[str, metain4File] = {} # key: file name, value: metain4File
        self.pieces: Dict[str, Dict[int, bytes]] = {} # key: file name, value: dict of piece index and piece data
        self.magnet_links: Dict[str, str] = {} # key: file name, value: magnet link
        
    # @tracker_connection
    # Give a chance to connect before its time out   
    # IF timeout send exception 
    def tracker_connection(self):
        attempts = 3
        for attempt in range(attempts):
            try:
                self.peer_tracker_socket= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.peer_tracker_socket.connect((SERVER_IP, PORT))
                print(f"The peer has been connected to tracker server at {SERVER_IP}:{PORT}")
                return
            except Exception as e:
                print(f"Attempt {attempt + 1}/{attempts} failed: {e}")
                if attempt < attempts - 1:
                    print("Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    print("Error connection to tracker after multiple tries.")
                    raise    
    
    # @signup
    # Handles the process of signing up a new user
    # Prompts the user for their username and password
    # Sends a registration request message to the tracker server with user details
    # Waits for the response from the server, and checks if registration is successful
    # If successful, creates a repository directory for the user if it doesn't exist
    # Sends a confirmation message to the user and returns the peer ID
    # If the registration fails, sends an error message to the user
    # Catches and handles any connection or unexpected errors during the signup process
    def signup(self):
        user_name = input("\nEnter your name: ")
        password = enter_Pasword()
        msg = {'type': REGISTER, 'user_name': user_name, 'password': password, 'ip': self.ip, 'port': self.port}
        try:
            print("Sign up process is loading...")
            msg = pickle.dumps({'type': REGISTER, 'user_name': user_name, 'password': password, 'ip': self.ip, 'port': self.port})
            self.peer_tracker_socket.sendall(struct.pack('>I', len(msg)) + msg)
            print("Loading....")
            
            rev_msg = receiveMess(self.peer_tracker_socket)
            if rev_msg is None:
                raise ConnectionError("Connection close: data received")
            print(f"Received {len(rev_msg)} bytes of data")
            result = pickle.loads(rev_msg)
            
            if result['type'] == REGISTER_SUCCESSFUL:
                print(f"User: {user_name}\n")
                peer_id = result['peer_id']
                print("Signup successfully!")
                if not os.path.exists(f"repository_{user_name}"):
                    os.makedirs(f"repository_{user_name}")
                    print("We have created your repository")
                else:
                    print("The system already created")
                self.user_name = user_name
                return peer_id
            else:
                print(f"User: {user_name} cant register")
                print(result['message'])
                return None
        except ConnectionResetError:
            print("Connection was reset and closed unexpectedly")
            return None
        except Exception as e:
            print(f"An error occured: {e}")
            return None
    
    # @login
    # Handles the process of logging in a user
    # Prompts the user for their username and password
    # Sends a login request message to the tracker server with user credentials
    # Waits for the response from the server and checks if login is successful
    # If successful, retrieves the peer ID and confirms the login
    # If the login fails, checks the error type and handles the following cases:
    #   - Incorrect password: Prompts the user to try logging in again
    #   - User does not exist: Redirects the user to the signup process
    #   - Internal server error: Displays a generic error message
    # Catches and handles any connection or unexpected errors during the login process
    def login(self):
        user_name = input("\nEnter your name: ")
        password = enter_Pasword()
        self.user_name = user_name
        msg = {'type': LOGIN, 'user_name': user_name, 'password': password, 'ip': self.ip, 'port': self.port}
        try:
            print("Log in process is loading...")
            msg = pickle.dumps({'type': LOGIN, 'user_name': user_name, 'password': password, 'ip': self.ip, 'port': self.port})
            self.peer_tracker_socket.sendall(struct.pack('>I', len(msg)) + msg)
            print("Loading....")
            
            rev_msg = receiveMess(self.peer_tracker_socket)
            if rev_msg is None:
                raise ConnectionError("Connection close: data received")
            
            print(f"Received {len(rev_msg)} bytes of data")
            result = pickle.loads(rev_msg)
            print(result['type'])
            if result['type'] == LOGIN_SUCCESSFUL:
                print(f"User: {user_name}\n")
                self.peer_id = result['peer_id']
                print("Login successfully!")
                return self.peer_id
            else:
                print(f"User cant login {user_name}")
                print(result['message'])
                if result['type'] == LOGIN_WRONG_PASSWORD:
                    print("The password is incorrect")
                    print("Please try again.")
                    self.login()
                    return None
                elif result['type'] == LOGIN_ACC_NOT_EXIST:
                    print("User does not exist. Moving to the signup...")
                    self.signup()
                    return None
                else:
                    print("Internal server error")
                    return None
        except Exception as e:
            print(f"Issue occurred during login process: {e}")
        pass
    
    # @create_torrent
    # Handles the process of creating a torrent file for a given file
    # Checks if the file exists at the specified file path
    # If the file exists, retrieves its name and size, and generates an info hash using SHA1 of the file name
    # Splits the file into pieces with a predefined piece size
    # Constructs the metainfo dictionary containing the file name, file size, piece length, number of pieces, and the tracker address
    # Stores the metainfo and pieces in the `files` and `pieces` attributes respectively
    # Returns the metainfo dictionary containing information about the file and its pieces
    # If the file doesn't exist, prints an error message and returns None
    def create_torrent(self, file_path: str):
        print("Creating torrent...")
        if not os.path.exists(file_path):
            print(f"File {file_path} does not exist.")
            return

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        info_hash = hashlib.sha1(file_name.encode()).hexdigest()
        pieces = file_into_pieces(file_path, PIECE_SIZE)
        tracker_address = f"http://{SERVER_IP}:{PORT}"
        metainfo = {
            'file_name': file_name,
            'file_size': file_size,
            'piece_length': PIECE_SIZE,
            'pieces_count': len(pieces),
            'announce': tracker_address
        }
        self.files[file_name] = metainfo
        self.pieces[file_name] = {i: piece for i, piece in enumerate(pieces)}
        return metainfo
    
    # @upload_file
    # Handles the process when a peer uploads a file to the tracker
    # First checks if the peer is logged in by verifying the `peer_id`
    # Prompts the user to input the file name they want to upload, including its extension
    # Generates a torrent file (metainfo) for the selected file using `create_torrent`
    # Sends an upload file request to the tracker with the file's metainfo and peer ID
    # Waits for a response from the tracker
    # If the upload is successful, prints the success message and the generated magnet link
    # Saves the magnet link in the peer's local repository directory as a file
    # If the upload fails, prints an error message returned by the tracker
    # Handles any exceptions that may occur during the file upload process
    def upload_file(self):
        if self.peer_id is None:
            print("The peer has to log in first.")
            return
        
        file_path = str(input("Type file name you want to upload(including format extension): "))
        file_path = 'repository_' + self.user_name + '/' + file_path
        metainfo = self.create_torrent(file_path)
        try:
            print("An upload file request is sending...")
            
            message = pickle.dumps({'type': UPLOAD_FILE, 'metainfo': metainfo, 'peer_id': self.peer_id})
            self.peer_tracker_socket.sendall(struct.pack('>I', len(message)) + message)
            
            print("Request has been sent. Awaiting a response from the tracker...")
            dataResponsive = receiveMess(self.peer_tracker_socket)
            if dataResponsive is None:
                raise ConnectionError("Close the connection while data is being received")
            print(f"Received {len(dataResponsive)} bytes of data")
            response = pickle.loads(dataResponsive)
            if response['type'] == UPLOAD_FILE_COMPLETE:
                print(f"File {file_path} uploaded completely")
                magnet_link = response['magnet_link']
                print(f"Magnet link: {magnet_link}")
                with open(os.path.join(f"repository_{self.user_name}", f"{metainfo['file_name']}_magnet"), 'wb') as f:
                    f.write(magnet_link.encode())
            else:
                print(f"File {file_path} can not upload")
                print(response['message'])
        except Exception as e:
            print(f"An issue occurred during upload file: {e}")
            
    # @logout
    # Handles the process when a peer logs out from the tracker
    # First checks if the peer is logged in by verifying the `peer_id`
    # Sends a logout request to the tracker with the peer's ID
    # Waits for a response from the tracker
    # If the logout is successful, prints a confirmation message
    # If the logout fails, prints an error message returned by the tracker
    # Handles any issues or errors that occur during the logout process
    def logout(self):
        if not self.peer_id:
            print("The peer has to log in first.")
            return
        message = pickle.dumps({'type': LOGOUT, 'peer_id': self.peer_id})
        self.peer_tracker_socket.sendall(struct.pack('>I', len(message)) + message)
        print("A logout request has been sent. Awaiting a response from the tracker...")
        dataResponsive = receiveMess(self.peer_tracker_socket)
        if dataResponsive is None:
            raise ConnectionError("Close the connection while data is being received")
        response = pickle.loads(dataResponsive)
        if response['type'] == LOGOUT_SUCCESSFUL:
            print("Logout completely")
        else:
            print("Can not log out")
            print(response['message'])
    
    # @listen_to_peers
    # Listens for incoming connections from peers
    # Continuously accepts new connections from peer peers through the server socket
    # For each new connection, a new thread is created to handle the peer's interaction
    # The `peers_connection` method is called in a separate thread to manage the communication with the connected peer
    # If the server socket is not initialized or an error occurs, the loop breaks or the error is handled
    # In case of a socket closure error (OSError), the server socket is closed and the listening loop is stopped
    def listen_to_peers(self):
        while True:
            try:
                if not self.peer_peers_socket:
                    print("Server socket is not initialized")
                    break
                another_peer_peers, addr = self.peer_peers_socket.accept()
                print(f"There is a new connection from {addr}")
                client_thread = threading.Thread(target=self.peers_connection, 
                                                args=(another_peer_peers, addr))
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                if isinstance(e, OSError) and e.winerror == 10038:
                    print("Close the server socket")
                    break
                print(f"Error accepting connection: {e}")
    
    # @peers_connection
    # Handles the communication with a connected peer
    # Listens for incoming messages from the peer and processes them based on the message type
    # Verifies the magnet link or responds with a requested piece of data
    # Closes the connection with the peer once the communication is finished or an error occurs
    # Handles any exceptions during communication and logs the error
    def peers_connection(self, peer_socket, addr):
        print(f"Handling connection from {addr}")
        while True:
            try:
                print(f"Waiting for data from {addr}")
                data = receiveMess(peer_socket)
                if data is None:
                    print(f"Client {addr} disconnected")
                    break
                print(f"Received {len(data)} bytes from {addr}")
                info = pickle.loads(data)
                print(f"Received message from {addr}: {info['type']}")
                if info['type'] == VERIFY_MAGNET_LINK:
                    self.verify_magnet_link(peer_socket, info)
                elif info['type'] == REQUEST_PIECE:
                    self.piece_respone(peer_socket, info)
                    
            except Exception as e:
                print(f"Error handling peer {addr}: {e}")
                traceback.print_exc()
                break
        peer_socket.close()
        print(f"Connection closed for {addr}")
    
    # @piece_respone
    # Handles the request for a specific piece of a file from a peer
    # Retrieves the requested file and sends the corresponding piece to the peer
    # Sends the piece back to the peer using the 'SEND_PIECE' message type
    def piece_respone(self, peer_socket, info):
        file_name = info['file_name']
        piece_index = info['piece_index']
        file_path = f"repo_{self.user_name}/{file_name}"
        pieces = send_piece(file_path, PIECE_SIZE, piece_index)
        sendMess(peer_socket, {'type': SEND_PIECE, 'pieces': pieces})
        
    # @verify_magnet_link
    # Handles the verification of a magnet link from a peer
    # Compares the received magnet link with the stored magnet link for the requested file
    # Sends a response back to the peer, confirming or rejecting the link verification
    # If an error occurs, sends an error response with the exception message
    def verify_magnet_link(self, peer_socket, info):
        try:
            # Nhận verification request
            magnet_link = info['magnet_link']
            file_name = info['file_name']
            print(f'Received the magnet link from {magnet_link}')
            
            with open(f"repository_{self.user_name}/{file_name}_magnet", 'rb') as f:
                magnet_link_to_verify = f.read().decode('utf-8')
                
            print(f'Confirm the magnet link: {magnet_link_to_verify}')
            
            if magnet_link == magnet_link_to_verify:
                print(f"Confirmed the magnet link for {file_name}")
                response = {'type': VERIFY_MAGNET_LINK_SUCCESSFUL}
            else:
                print(f"There is an error in confirming magnet link for {file_name}")
                response = {'type': VERIFY_MAGNET_LINK_FAILED}
        
            sendMess(peer_socket, response)
        except Exception as e:
            print(f"Error handling magnet link verification: {e}")
            error_response = pickle.dumps({'type': 'ERROR', 'message': str(e)})
            sendMess(peer_socket, error_response)
    
    # @tracker_socket
    # Initializes the server socket to listen for incoming peer connections
    # Binds the socket to the specified IP and port, and sets it to listen for up to 5 peer connections
    # Prints the status of the server socket initialization and handles any errors during the setup
    def tracker_socket(self):
        try:
            self.peer_peers_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.peer_peers_socket.bind((self.ip, self.port))
            self.peer_peers_socket.listen(5) #giả sử rằng chúng ta chỉ lắng nghe từ 5 người ngang hàng cùng một lúc
            print(f"Listening for incoming connections on {self.ip}:{self.port}")
        except Exception as e:
            print(f"There is an error in initializing tracker socket: {e}")
            traceback.print_exc()
    
    # @clean_up
    # Cleans up by closing the server and peer connection sockets
    # Ensures proper closure of sockets, handling any potential errors during the cleanup process
    def clean_up(self):
        try:
            if self.peer_peers_socket:
                self.peer_peers_socket.close()
            if self.peer_tracker_socket:
                self.peer_tracker_socket.close()
        except Exception as e:
            print(f"Error cleaning up: {e}")
            traceback.print_exc()
            
    def peer_Controll(self):
        try:
            self.tracker_socket()
            self.listen_thread = threading.Thread(target=self.listen_to_peers)
            self.listen_thread.daemon = True
            self.listen_thread.start()
            while True:
                print("\n       ==== Control Panel ======")
                print("1. Upload files(.pdf, .docx, .txt, ...)")
                print("2. Download files(.pdf, .docx, .txt, ...)")
                print("3. Exit")
                
                choice = input("\nPlease choose 1-3: ")
                
                if choice == '1':
                    self.upload_file()
                elif choice == '2':
                    #self.download_file()
                    break
                elif choice == '3':
                    self.logout()
                    self.clean_up()
                    print("Exiting...")
                    break
                else:
                    print("That's not a valid choice. Please try again.")
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()
            
            
if __name__ == '__main__':
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    peer_port = int(input("Type the peer port: "))
    peer = None
    try:
        peer = Peer(local_ip, peer_port)
        peer.tracker_connection()
        print('\nChoose your Options:')
        print('1. Signup')
        print('2. Login')
        while True:
            choice = int(input('\nPlease choose 1-2: '))
            if choice == 1:
                peer_id = peer.signup()
                if peer_id:
                    print(f"The user ID: {peer_id}")
            elif choice == 2:
                peer_id = peer.login()
                if peer_id:
                    print(f'The peer id is {peer_id}')
                    break
                break
            else:
                print('Invalid choice')
        peer.peer_Controll()
    except Exception as e:
        print(f"An error occurred: {e}")
    except KeyboardInterrupt:
        print("Program interrupted by the peer.")
    finally:
        if peer and peer.peer_peers_socket:
            peer.peer_peers_socket.close()
        print("Closing the connection and exiting the program.")
        input("Press Enter to exit...")
