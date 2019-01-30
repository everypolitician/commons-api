from ..settings import *

SECRET_KEY = 'Acha9ohp2gae3chae7zeiwoo0Juhe2ooShu5eeP5wieL2ooxah1Aenie7Eim7cha'

# https://stackoverflow.com/a/18601897
import socket
def guard(*args, **kwargs):
    raise Exception("I told you not to use the Internet!")
socket.socket = guard