import socket
import threading

from network import receive


class Client:
    def __init__(self, host: str, port: int) -> None:
        self._from_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._from_server.connect((host, port))
        self._from_server.setblocking(False)

        print("Connected to server")

        self._running = False

    def run(self):
        self._running = True

        # Create a thread for updating the state of the game
        state_thread = threading.Thread(target=self._update_state, daemon=True)
        state_thread.start()

        # Wait for threads to finish
        state_thread.join()

        # Close server connection
        self._from_server.close()

    def _update_state(self):
        while self._running:
            data = receive([self._from_server])

            print(data)
