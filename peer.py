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
        self.peer_peers = None
        self.peer_tracker = None
        
        self.files: Dict[str, metain4File] = {} # key: file name, value: metain4File
        self.pieces: Dict[str, Dict[int, bytes]] = {} # key: file name, value: dict of piece index and piece data
        self.magnet_links: Dict[str, str] = {} # key: file name, value: magnet link
        
    # @trackerConnection
    # Give a chance to connect before its time out   
    # IF timeout send exception 
    def trackerConnection(self):
        attempts = 3
        for attempt in range(attempts):
            try:
                self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.peer_socket.connect((SERVER_IP, PORT))
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
                
if __name__ == '__main__':
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    peer_port = int(input("Type the peer port: "))
    peer = None
    try:
        peer = Peer(local_ip, peer_port)
        peer.trackerConnection()
        print('\nChoose your Options:')
        print('1. Signup')
        print('2. Login')
        while True:
            choice = int(input('\nPlease choose 1-2: '))
            if choice == 1:
                break
            elif choice == 2:
                break
            else:
                print('Invalid choice')
        #peer.peerMenu()
    except Exception as e:
        print(f"An error occurred: {e}")
    except KeyboardInterrupt:
        print("Program interrupted by the peer.")
    finally:
        if peer and peer.peer_socket:
            peer.peer_socket.close()
        print("Closing the connection and exiting the program.")
        input("Press Enter to exit...")
