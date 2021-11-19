import socket
import threading

import pygame
from config import UPDATE_RATE
from network import receive, send


class Client:
    def __init__(self, host: str, port: int, client_name: str) -> None:
        self._client_name = client_name

        self._from_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._from_server.connect((host, port))
        self._from_server.setblocking(False)

        self._to_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._to_server.connect((host, port + 1))
        self._to_server.setblocking(False)

        send([self._to_server], self._client_name)

        print("Connected to server")

        self._state = None

        self._running = False

    def run(self):
        self._running = True

        # Create a thread for updating the state of the game
        state_thread = threading.Thread(target=self._from_server_handle, daemon=True)
        state_thread.start()

        # Create a thread for controlling client from terminal
        command_thread = threading.Thread(target=self._process_input, daemon=True)
        command_thread.start()

        # Wait for threads to finish
        state_thread.join()
        command_thread.join()

        # Close server connection
        self._from_server.close()
        self._to_server.close()

    def _from_server_handle(self):
        screen = pygame.display.set_mode((200, 200))
        while self._running:
            [data] = receive([self._from_server])
            if data["type"] == "state":
                self._state = data["state"]

            print(self._state)

            screen.fill((0, 0, 0))

            font = pygame.font.Font(None, 74)
            text = font.render(self._client_name, 1, (255, 255, 255))
            screen.blit(text, (10, 10))

            pygame.display.flip()

    def _process_input(self):
        """
        Send user's input command to server
        """
        clock = pygame.time.Clock()
        while self._running:
            # Exit the game if user hits close
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    break

            # Get keys pressed by user
            keys = pygame.key.get_pressed()

            data = None

            if self._state is not None:
                if keys[pygame.K_SPACE]:
                    if self._state[self._client_name] == 0:
                        data = {}
                        data["type"] = "command"
                        data["sender"] = self._client_name
                        data["command"] = "tap"
                elif self._state[self._client_name] == 1:
                    data = {}
                    data["type"] = "command"
                    data["sender"] = self._client_name
                    data["command"] = "untap"

            if data is not None:
                send([self._to_server], data)

            clock.tick(UPDATE_RATE)
