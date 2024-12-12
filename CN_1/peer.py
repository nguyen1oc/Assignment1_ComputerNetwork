import socket
import threading
import sqlite3
import time
import json #JavaScript Object Notation convert to jason type
import os
import sys
import hashlib
import maskpass #using for hide the password
import pickle
import random
from tracker import listen_for_discovery

from command import *
from torrent import *
from support import *


SERVER_NAME = socket.gethostname()
SERVER_IP = "10.127.3.77"
PORT = 1606

class Peer:
    # @__init__
    # Creates a Peer instance with specified IP and port.
    # Sets up sockets for tracker and peer communication.
    # Initializes storage for files, file pieces, and magnet links.
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
    # Connects the peer to the tracker server.
    # Attempts connection up to 3 times with a 5-second delay between retries.
    # Prints success or failure messages and raises an error if all attempts fail.
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
                print(result['msg'])
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
        password = maskpass.askpass(prompt="Enter your password: ", mask="*")
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
                print(f"User cant login: {user_name}")
                print(result['msg'])
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
    # Can upload multiple files (separate by commas)
    # Generates a torrent file (metainfo) for the selected file using `create_torrent`
    # Sends an upload file request to the tracker with the file's metainfo and peer ID
    # Waits for a response from the tracker
    # If the upload is successful, prints the success message and the generated magnet link
    # Saves the magnet link in the peer's local repository directory as a file
    # If the upload fails, prints an error message returned by the tracker
    # Handles any exceptions that may occur during the file upload process
    def upload_files(self):
        if self.peer_id is None:
            print("You must log in first.")
            return

        file_paths = input("Enter the file names you want to upload (separate by commas): ").split(',')
        file_paths = [file.strip() for file in file_paths] 
        
        for file_path in file_paths:
            full_file_path = f'repository_{self.user_name}/{file_path}'
            
            metainfo = self.create_torrent(full_file_path)
            if not metainfo:
                print(f"Skipping {file_path} as it doesn't exist.")
                continue
            
            try:
                print(f"Sending upload request for file: {file_path}...")
                
                msg = pickle.dumps({'type': UPLOAD_FILE, 'metainfo': metainfo, 'peer_id': self.peer_id})
                self.peer_tracker_socket.sendall(struct.pack('>I', len(msg)) + msg)
                
                # Nhận phản hồi từ tracker
                print("Awaiting response from the tracker...")
                rev_msg = receiveMess(self.peer_tracker_socket)
                if rev_msg is None:
                    raise ConnectionError("Connection was closed while receiving data.")
                
                response = pickle.loads(rev_msg)
                if response['type'] == UPLOAD_FILE_COMPLETE:
                    print(f"File {file_path} uploaded successfully.")
                    magnet_link = response['magnet_link']
                    print(f"Magnet link: {magnet_link}")
                    
                    # Lưu magnet link vào thư mục repository
                    with open(os.path.join(f"repository_{self.user_name}", f"{metainfo['file_name']}_magnet"), 'wb') as f:
                        f.write(magnet_link.encode())
                else:
                    print(f"Failed to upload file {file_path}: {response['msg']}")
            
            except Exception as e:
                print(f"An error occurred while uploading {file_path}: {e}")
        
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
        msg = pickle.dumps({'type': LOGOUT, 'peer_id': self.peer_id})
        self.peer_tracker_socket.sendall(struct.pack('>I', len(msg)) + msg)
        print("A logout request has been sent. Awaiting a response from the tracker...")
        rev_msg = receiveMess(self.peer_tracker_socket)
        if rev_msg is None:
            raise ConnectionError("Close the connection while data is being received")
        result = pickle.loads(rev_msg)
        if result['type'] == LOGOUT_SUCCESSFUL:
            print("Logout completely")
        else:
            print("Can not log out")
            print(result['msg'])
          
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
    
    # @get_list_files_to_download
    # Fetches the list of files available for download from the tracker server.
    # Ensures the peer is logged in before sending the request.
    # Sends a request message to the tracker and waits for a response.
    # Parses and returns the list of files if available; otherwise, informs that no files are found.
    # Raises an error if the connection is interrupted during data reception.
    def get_list_files_to_download(self):
        if not self.peer_id:
            print("The peer has to log in first.")
            return
        msg = pickle.dumps({'type': GET_LIST_FILES_TO_DOWNLOAD})
        self.peer_tracker_socket.sendall(struct.pack('>I', len(msg)) + msg)
        rev_msg = receiveMess(self.peer_tracker_socket)
        if rev_msg is None:
            raise ConnectionError("Close the connection while data is being received")
        result = pickle.loads(rev_msg)
        if result['type'] == GET_LIST_FILES_TO_DOWNLOAD and result['files']:
            return result['files']
        else:
            print("There are no files available")
    
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
                print(f"Received msg from {addr}: {info['type']}")
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
        file_path = f"repository_{self.user_name}/{file_name}"
        pieces = send_piece(file_path, PIECE_SIZE, piece_index)
        sendMess(peer_socket, {'type': SEND_PIECE, 'pieces': pieces})
        
    # @request_piece
    # Requests a specific piece of a file from another peer.
    # Establishes a temporary socket connection to the peer at the specified IP and port.
    # Sends a message containing the request type, file name, and piece index.
    # Waits for a response and closes the connection after receiving it.
    # Parses the response and returns the requested piece data.
    # Raises an error if the connection is interrupted during data reception.
    def request_piece(self, ip, port, info):
        temp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        temp_socket.connect((ip, port))
        msg = {'type': REQUEST_PIECE, 'file_name': info['file_name'], 'piece_index': info['piece_index']}
        sendMess(temp_socket, msg)
        rev_msg = receiveMess(temp_socket)
        temp_socket.close()
        if rev_msg is None:
            raise ConnectionError("Close the connection while data is being received")
        result = pickle.loads(rev_msg)
        return result['pieces']
    
    
    def download_files(self):
        files = self.get_list_files_to_download()
        if not files:
            print("There are no files available to download.")
            return

        print("All available files:")
        available_files = []
        for file in files:
            if not os.path.exists(f"repository_{self.user_name}/{file}"):
                print(file)
                available_files.append(file)

        if not available_files:
            print("No new files to download.")
            return

        file_names = input("Type the file names to download (separate by commas): ").split(',')

        files_to_download = [file for file in file_names if file in available_files]
        if not files_to_download:
            print("No valid files found in your input.")
            return

        print(f"Files to download: {', '.join(files_to_download)}")

        for file_name in files_to_download:
            print(f"Starting download for {file_name}...")
            self.download_file_single(file_name)

    def download_file_single(self, file_name):
        start_time = time.time()
        msg = pickle.dumps({'type': REQUEST_FILE, 'file_name': file_name})
        self.peer_tracker_socket.sendall(struct.pack('>I', len(msg)) + msg)
        rev_msg = receiveMess(self.peer_tracker_socket)
        if rev_msg is None:
            raise ConnectionError("Connection closed while receiving data from tracker.")
        result = pickle.loads(rev_msg)
        
        if result['type'] == SHOW_PEER_HOLD_FILE:
            print(f"Found file {file_name} on tracker.")
            metainfo = result['metainfo']
            ip_port_list = result['ip_port_list']
            print(f'Found {len(ip_port_list)} peers for this file.')
        
            verify_result = []
            magnet_link = magnet_Link(metainfo, SERVER_IP, PORT)
            for ip, port in ip_port_list:
                res = self.send_confirm_magnet(magnet_link=magnet_link, ip=ip, port=port, file_name=file_name)
                if res:
                    verify_result.append((ip, port))
            
            if verify_result:
                print(f"Peers that have the file: {', '.join([f'{ip}:{port}' for ip, port in verify_result])}")

                # Phân bổ mảnh tệp cho từng peer
                piece_per_peer = metainfo['pieces_count'] // len(verify_result)
                remaining_pieces = metainfo['pieces_count'] % len(verify_result)

                peer_and_piece_index: Dict[Tuple[str, int], List[int]] = {}

                # Phân phối mảnh tệp chính
                for i, (ip, port) in enumerate(verify_result):
                    start_index = i * piece_per_peer
                    end_index = start_index + piece_per_peer
                    peer_and_piece_index[(ip, port)] = list(range(start_index, end_index))

                # Phân phối mảnh tệp còn lại
                for i in range(remaining_pieces):
                    peer_and_piece_index[(verify_result[i][0], verify_result[i][1])].append(piece_per_peer * len(verify_result) + i)

                # Hiển thị thông tin về các mảnh tệp mà peer cần cung cấp
                for ip, port in peer_and_piece_index:
                    print(f"Peer {ip}:{port} will provide pieces: {peer_and_piece_index[(ip, port)]}")

                # Tải các mảnh tệp từ từng peer
                piece_received = []
                total_piece = 0
                for ip, port in peer_and_piece_index:
                    list_piece_index = peer_and_piece_index[(ip, port)]
                    msg = {'file_name': file_name, 'piece_index': list_piece_index}
                    result = self.request_piece(ip, port, msg)
                    
                    if result:  # Kiểm tra nếu có mảnh tệp
                        print(f"Received {len(result)} pieces from {ip}:{port}")
                        for i, piece in enumerate(result):
                            piece_received.append({'piece_index': list_piece_index[i], 'piece': piece})
                        total_piece += len(result)
                
                if total_piece != metainfo['pieces_count']:
                    print(f"Received {total_piece} pieces, but expected {metainfo['pieces_count']} pieces")
                    return
                
                piece_received.sort(key=lambda x: x['piece_index'])
                with open(os.path.join(f"repository_{self.user_name}", file_name), 'wb') as f:
                    for piece in piece_received:
                        f.write(piece['piece'].get('piece'))
                
                end_time = time.time()
                print(f"Downloaded file {file_name} completely.")
                download_time = end_time - start_time
                print(f"Downloaded file {file_name} completely in {download_time:.2f} seconds.")
            else:
                print("No peers found")




    # @send_confirm_magnet
    # Sends a request to verify the magnet link with a specific peer.
    # 1. Establishes a temporary TCP connection to the peer using the given IP and port.
    # 2. Sends a message containing the magnet link and file name for verification.
    # 3. Waits for a response from the peer:
    #    - If successful, returns `True`.
    #    - If an error occurs or verification fails, returns `False`.
    # 4. Handles exceptions such as connection issues or data errors.
    # 5. Ensures the socket is closed after the operation, regardless of success or failure.
    def send_confirm_magnet(self, magnet_link, ip, port, file_name):
        temp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            temp_socket.connect((ip, port))
            msg = {'type': VERIFY_MAGNET_LINK, 'magnet_link': magnet_link, 'file_name': file_name}
            sendMess(temp_socket, msg)
            rev_msg = receiveMess(temp_socket)
            if rev_msg is None:
                raise ConnectionError("Close the connection while data is being received")
                
            result = pickle.loads(rev_msg)
            return result['type'] == VERIFY_MAGNET_LINK_SUCCESSFUL
        except Exception as e:
            print(f"Error verifying magnet link with peer {ip}:{port}: {e}")
            return False
        finally:
            temp_socket.close() 

    # @verify_magnet_link
    # Handles the verification of a magnet link from a peer
    # Compares the received magnet link with the stored magnet link for the requested file
    # Sends a response back to the peer, confirming or rejecting the link verification
    # If an error occurs, sends an error response with the exception message
    def verify_magnet_link(self, peer_socket, info):
        try:
            magnet_link = info['magnet_link']
            file_name = info['file_name']
            print(f'Received the magnet link from {magnet_link}')
            
            with open(f"repository_{self.user_name}/{file_name}_magnet", 'rb') as f:
                magnet_link_to_verify = f.read().decode('utf-8')
                
            print(f'Confirm the magnet link: {magnet_link_to_verify}')
            
            if magnet_link == magnet_link_to_verify:
                print(f"Confirmed the magnet link for {file_name}")
                result = {'type': VERIFY_MAGNET_LINK_SUCCESSFUL}
            else:
                print(f"There is an error in confirming magnet link for {file_name}")
                result = {'type': VERIFY_MAGNET_LINK_FAILED}
        
            sendMess(peer_socket, result)
        except Exception as e:
            print(f"Error handling magnet link verification: {e}")
            error_response = pickle.dumps({'type': 'ERROR', 'msg': str(e)})
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
                    self.upload_files()
                elif choice == '2':
                    self.download_files()
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
        while True:
            print('\nChoose your Options:')
            print('1. Signup')
            print('2. Login')
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
                else:
                    print("Login failed, exiting program...")
                    sys.exit()    
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
