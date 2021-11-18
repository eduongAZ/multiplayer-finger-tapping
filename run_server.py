from server import Server
from config import SERVER_ADDR


if __name__ == "__main__":
    server = Server(SERVER_ADDR, 6060)
    server.run()
