import socket
import threading
from select import select

from config import (SECONDS_COUNT_DOWN, SECONDS_PER_SESSION, SESSION,
                    UPDATE_RATE)
from network import receive, send
from pygame import time

from .utils import TAPPED, UNTAPPED


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

        print(f"Address: {host}, {port}")

        self._to_client_connections = []
        self._from_client_connections = {}

        self._state = {}

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

        from_client_commands_thread = threading.Thread(target=self._from_client_commands, daemon=True)
        from_client_commands_thread.start()

        print("Server started")

        # Wait for threads to finish
        to_client_request_thread.join()
        from_client_request_thread.join()
        to_client_update_state_thread.join()
        from_client_commands_thread.join()

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
                self._state[client_name] = UNTAPPED
                self._thread_lock.release()

                print("Receiving commands from [" + client_name + ", " + client_addr[0] + ", " + str(client_addr[1]) + ']')

    def _to_client_update_state(self):
        data = {}
        data["type"] = "state"

        current_session_index = -1
        counter_target = SECONDS_COUNT_DOWN

        start_ticks = time.get_ticks()

        seconds = 0.0

        clock = time.Clock()
        while self._running:
            if seconds >= counter_target:
                current_session_index += 1

                if current_session_index >= len(SESSION):
                    self._running = False
                    break

                counter_target = SECONDS_PER_SESSION[current_session_index]
                start_ticks = time.get_ticks()

            if self._to_client_connections:
                data["state"] = self._state
                data["reveal"] = 1 if current_session_index < 0 else SESSION[current_session_index]

                seconds_to_send = int(counter_target) - int(seconds)
                data["seconds"] = 1 if seconds_to_send == 0 else seconds_to_send

                send(self._to_client_connections, data)

            seconds = (time.get_ticks() - start_ticks) / 1000.0

            clock.tick(UPDATE_RATE)

    def _from_client_commands(self):
        while self._running:
            all_data = receive(self._from_client_connections.keys(), 0.1)

            for data in all_data:
                if data["type"] == "command":
                    if data["command"] == "tap":
                        self._state[data["sender"]] = TAPPED
                    else:
                        self._state[data["sender"]] = UNTAPPED
