from typing import Dict, Set, List, Tuple
import bencodepy #FOR ENCODE AND DECODE
import traceback
import struct #METHOD PACK AND UNPACK THE BINARY
import pickle

HEADER = 10
QUEUE_SIZE = 5
PIECE_SIZE = 512 * 1024 
FORMAT = 'utf-8'

DISCONNECT_MSG = '!DISCONNECT'
#REGISTER
REGISTER = 'register'
REGISTER_FAILED = 'register_error'
REGISTER_SUCCESSFUL = 'register_completed'
REQUEST = 'request_file'

#LOGIN
LOGIN = 'login'
LOGIN_SUCCESSFUL = 'login_completed'
LOGIN_FAILED = 'login_error'
LOGIN_WRONG_PASSWORD = 'invalid_password'
LOGIN_ACC_NOT_EXIST = 'account_not_found'

#LOGOUT
LOGOUT = 'logout'
LOGOUT_SUCCESSFUL = 'logout_complete'

#UPLOAD FILE
UPLOAD_FILE = 'upload_file'
UPLOAD_FILE_COMPLETE = 'upload_file_complete'
UPLOAD_FILE_ERROR = 'upload_file_error'

#CONTROL
GET_LIST_FILES_TO_DOWNLOAD = 'get_list_files_for_download'
DOWNLOAD_FILE = 'download_file'
REQUEST_FILE = 'request_file'
SHOW_PEER_HOLD_FILE = 'show_peer_hold_file'
SHOW_PEER_HOLD_FILE_FAILED = 'show_peer_hold_file_error'
REQUEST_PIECE = 'request_piece'
SEND_PIECE = 'send_piece'

#VERIFY
VERIFY_MAGNET_LINK = 'confirm_magnet_link'
VERIFY_MAGNET_LINK_SUCCESSFUL = 'confirm_magnet_link_complete'
VERIFY_MAGNET_LINK_FAILED = 'confirm_magnet_link_complete'