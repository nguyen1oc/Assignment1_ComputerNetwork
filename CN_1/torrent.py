import hashlib #hash
from dataclasses import dataclass #support to create __init__, __reqr__, __eq__
from typing import List, Dict
import bencodepy
from command import *


@dataclass
class File:
    name: str
    size: int
    
    
@dataclass
class Piece:   
    index: int
    hash: str
    
# @metain4File
# help support decode and encode torrent
class metain4File:
    # @___init__
    # Constructor for the meatin4file
    # info_hash of the torrent, specify which file
    # list of piece (stand for the part of file)
    # the information of file (its name and size)
    # the ip of tracker where peer contact and requestfile
    def __init__(self, info_hash: str, pieces: List[Piece], file: File, tracker_ip: str):
        self.info_hash = info_hash
        self.pieces = pieces
        self.file = file
        self.tracker_ip = tracker_ip
        
    # @encode and @decode
    # encode and decode file through the process
    def encode(self) -> bytes:
        info = {
            'file_name': self.file.name,
            'file_size': self.file.size,
            'piece length': PIECE_SIZE,
            'pieces_count': len(self.pieces)
        }
        return bencodepy.encode({
            'info': info,
            'tracker_ip': self.tracker_ip
        })
        
    # decoded = {
    # 'info': {
    #     'file_name': 'examplefile.txt',
    #     'file_size': 123456,
    #     'pieces': [b'abc', b'def', b'ghi'], 
    # },
    # 'announce': 'abcxyz'
    # }    
        
    def decode(self, metainfo: bytes) -> 'metain4File':
        decoded = bencodepy.decode(metainfo)
        return metain4File(
            info_hash=hashlib.sha1(decoded['info']).hexdigest(),
            pieces=[Piece(index=i, hash=piece) for i, piece in enumerate(decoded['info']['pieces'])],
            file=File(name=decoded['info']['file_name'], size=decoded['info']['file_size']),
            tracker_ip=decoded['announce']
        )
 
class magnetText:
    # @__init__
    # Constructor for the magnetText
    # info_hash of the torrent, specify which file
    # the ip of tracker where peer contact and requestfile
    def __init__(self, info_hash: str, tracker_ip: str):
        self.info_hash = info_hash
        self.tracker_ip = tracker_ip

    # @to_string
    # Create a magnet link betwen infohash and th ip of tracker
    def to_string(self) -> str:
        return f"magnet:?xt=urn:btih:{self.info_hash}&tr={self.tracker_ip}"
    
    # @decode
    # Unlink
    def decode(self, magnet_string: str) -> 'magnetText':
        parts = magnet_string.split('&')
        info_hash = parts[0].split(':')[-1]
        tracker_ip = parts[1].split('=')[-1]
        return magnetText(info_hash, tracker_ip)

