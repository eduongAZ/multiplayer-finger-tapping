import socket
import threading
from select import select

from network import receive, send


class Server:
    def __init__(self, host: str, port: int) -> None:
        # Establish connection where clients can get game state update
        self._to_client_request = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._to_client_request.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Reuse socket
        self._to_client_request.bind((host, port))
        self._to_client_request.setblocking(False)

        # Establish connection where clients send control commands
        self._from_client_request = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._from_client_request.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Reuse socket
        self._from_client_request.bind((host, port + 1))
        self._from_client_request.setblocking(False)

        self._to_client_connections = []
        self._from_client_connections = {}

        self._running = False

        self._thread_lock = threading.Lock()

    def run(self):
        self._running = True

        to_client_request_thread = threading.Thread(target=self._dispatch_to_client_request, daemon=True)
        to_client_request_thread.start()

        from_client_request_thread = threading.Thread(target=self._dispatch_from_client_request, daemon=True)
        from_client_request_thread.start()

        to_client_update_state_thread = threading.Thread(target=self._to_client_update_state, daemon=True)
        to_client_update_state_thread.start()

        print("Server started.")

        # Wait for threads to finish
        to_client_request_thread.join()
        from_client_request_thread.join()
        to_client_update_state_thread.join()

        # Close server connection
        self._to_client_request.close()
        self._from_client_request.close()

    def _dispatch_to_client_request(self):
        """
        Dispatch client's connection for receiving game state updates from server
        """
        # Listen for client connection
        self._to_client_request.listen()

        while self._running:
            # Check for connection request
            readable, _, _ = select([self._to_client_request], [], [self._to_client_request], 0.1)

            for connection in readable:
                client_conn, client_addr = connection.accept()
                client_conn.setblocking(False)

                self._to_client_connections.append(client_conn)

                print("Sending replies to [" + client_addr[0] + ", " + str(client_addr[1]) + ']')

    def _dispatch_from_client_request(self):
        """
        Establish connection to receive clients' command
        """
        # Listen for client connection
        self._from_client_request.listen()

        while self._running:
            # Check for connection request
            readable, _, _ = select([self._from_client_request], [], [self._from_client_request], 0.1)

            for connection in readable:
                client_conn, client_addr = connection.accept()
                client_conn.setblocking(False)

                [client_name] = receive([client_conn])

                self._thread_lock.acquire()
                self._from_client_connections[client_conn] = client_name
                self._thread_lock.release()

                print("Receiving commands from [" + client_name + ", " + client_addr[0] + ", " + str(client_addr[1]) + ']')

    def _to_client_update_state(self):
        data = {}
        data["type"] = "state"

        while self._running:
            if self._to_client_connections:
                data["state"] = {}
                send(self._to_client_connections, data)
