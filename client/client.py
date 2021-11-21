import socket
import threading

import pygame
from common import PlayerSquare
from config import BOX_WIDTH, UPDATE_RATE
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

        # Create a thread for controlling client from terminal
        client_input_thread = threading.Thread(target=self._client_input_handle, daemon=True)
        client_input_thread.start()

        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

        win_width, win_height = pygame.display.get_surface().get_size()
        main_player_coordinate = ((win_width - BOX_WIDTH) / 2, (win_height / 2) - BOX_WIDTH - 1)
        other_player_height = (win_height / 2) + 1
        other_player_width_offset = (BOX_WIDTH / 2) + 1

        while self._running:
            pygame.event.get()

            data = receive([self._from_server], 0.0)
            if not data:
                continue
            else:
                [data] = data

            if data["type"] == "state":
                self._state = data["state"]

            print(data)

            num_other_players = len(self._state) - 1
            counter = 0

            # Add sprites to sprite group
            all_sprites_list = pygame.sprite.Group()
            for name, state in self._state.items():
                if name == self._client_name:
                    color = (255, 0, 255) if state else (100, 0, 100)
                    subject = PlayerSquare(main_player_coordinate, color)
                    all_sprites_list.add(subject)
                elif num_other_players == 1:
                    color = (255, 255, 255) if state else (100, 100, 100)
                    subject = PlayerSquare((main_player_coordinate[0], other_player_height), color)
                    all_sprites_list.add(subject)
                elif counter == 0:
                    color = (255, 255, 255) if state else (100, 100, 100)
                    subject = PlayerSquare((main_player_coordinate[0] - other_player_width_offset, other_player_height), color)
                    all_sprites_list.add(subject)
                    counter += 1
                else:
                    color = (255, 255, 255) if state else (100, 100, 100)
                    subject = PlayerSquare((main_player_coordinate[0] + other_player_width_offset, other_player_height), color)
                    all_sprites_list.add(subject)

            screen.fill((0, 0, 0))

            # Draw sprite group
            all_sprites_list.draw(screen)

            pygame.display.flip()

        # Wait for threads to finish
        client_input_thread.join()

        # Close server connection
        self._from_server.close()
        self._to_server.close()

    def _client_input_handle(self):
        """
        Send user's input command to server
        """
        clock = pygame.time.Clock()
        while self._running:
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
                send([self._to_server], data, wait_time=0.0)

            clock.tick(UPDATE_RATE)
