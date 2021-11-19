import pygame

from client import Client
from config import SERVER_ADDR

if __name__ == "__main__":
    pygame.init()
    
    client = Client(SERVER_ADDR, 6060, "tom")
    client.run()
