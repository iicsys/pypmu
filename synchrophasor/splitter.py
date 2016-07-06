import multiprocessing
import threading
import socket
import logging

from sys import stdout
from synchrophasor.frame import *
from select import select
from time import time

__author__ = "Stevan Sandi"
__copyright__ = "Copyright (c) 2016, Tomo Popovic, Stevan Sandi, Bozo Krstajic"
__credits__ = []
__license__ = "BSD-3"
__version__ = "0.1"


class StreamSplitter(object):

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    def stream_handler(self, connection, address, buffer):

        client_name = multiprocessing.current_process().name
        self.logger.info("[%s] - Connection from %s:%d", client_name, address[0], address[1])

        # Wait for start command from connected PDC to start sending
        streaming_enabled = False

        try:
            while True:

                command = None
                readable, writable, exceptional = select([connection], [], [], 0)  # Check for client commands

                if readable:
                    data = connection.recv(self.buffer_size)  # TODO: Refactor this to recv_all

                    if data:
                        try:
                            # Try to get get message:
                            received_message = CommonFrame.convert2frame(data)

                            if isinstance(received_message, CommandFrame):
                                command = CommandFrame.get_command(received_message)
                                self.logger.info("[%s] - Received command: [%s] <- (%s:%d)", client_name, command,
                                                 address[0], address[1])
                            else:
                                self.logger.debug("[%s] - Received non-command frame [%s] <- (%s:%d)",
                                                  client_name, command, address[0], address[1])
                                pass

                        except FrameError as e:
                            self.logger.warning("[%s] - Received unknown message <- (%s:%d)", client_name,
                                                address[0], address[1])
                            self.logger.error(str(e))

                if command == 'start':
                    streaming_enabled = True
                elif command == 'stop':
                    # streaming_enabled = False
                    break
                elif command == 'header':
                    connection.sendall(self.source_header)
                elif command == 'cfg1':
                    connection.sendall(self.source_cfg1)
                elif command == 'cfg2':
                    connection.sendall(self.source_cfg2)
                elif command == 'cfg3':
                    connection.sendall(self.source_cfg3)

                if streaming_enabled and not buffer.empty():
                    connection.sendall(buffer.get())
                    self.logger.debug("[%s] - Message sent at [%f] -> (%s:%d)", client_name, time(), address[0],
                                      address[1])  # TODO: Remove this for better performance
        except Exception as e:
            print(e)
        finally:
            connection.close()
            self.logger.info("[%s] - Connection from %s:%d has been closed.", client_name, address[0], address[1])

    def acceptor(self):

        while True:
            self.logger.info("Waiting for connection on %s:%d", self.listen_ip, self.listen_port)

            # Accept a connection on the bound socket and fork a child process to handle it.
            conn, address = self.socket.accept()

            # Create Queue which will represent buffer for specific client and add it o list of all client buffers
            buffer = multiprocessing.Queue()
            self.client_buffers.append(buffer)

            process_name = 'PDC - (' + str(address[0]) + ':' + str(address[1]) + ')'
            process = multiprocessing.Process(name=process_name,
                                              target=self.stream_handler, args=(conn, address, buffer))
            # process.daemon = True
            process.start()

            # Close the connection fd in the parent, since the child process has its own reference.
            conn.close()

    def join(self):
        # threading.Thread.join() is not interruptible, so tight loop in a sleep-based join
        while self.listener.is_alive():
            self.listener.join(0.5)

    def run(self):

        # Listen for connection on listen_ip:listen_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create TCP socket
        self.socket.bind((self.listen_ip, self.listen_port))  # Bind on specified IP and port
        self.socket.listen(5)  # Listen for incoming connections

        self.listener = threading.Thread(target=self.acceptor)  # Run acceptor thread to handle new connection
        self.listener.daemon = True
        self.listener.start()

        # Connect to source PMU
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.source_ip, self.source_port))

        try:
            self.logger.info("[%s] - Connected to %s:%d", self.name, self.source_ip, self.source_port)

            # Get Header frame from PMU
            self.logger.info("[%s] - Requesting Header frame from %s:%d", self.name, self.source_ip, self.source_port)
            cf = CommandFrame(self.id, 'header')
            sock.sendall(cf.convert2bytes())

            # Wait for Header frame TODO: Implement receive_all()
            header_frame = sock.recv(self.buffer_size)

            # TODO: validate Header Frame
            self.source_header = header_frame
            self.logger.info("[%s] - Received Header frame from %s:%d", self.name, self.source_ip, self.source_port)

            # # Get Configuration frame 1 from PMU
            # self.logger.info("[%s] - Requesting Configuration frame 1 from %s:%d", self.name, self.source_ip,
            #                  self.source_port)
            # cfg = CommandFrame(self.id, 'cfg1')
            # sock.sendall(cfg.convert2bytes())
            #
            # # Wait for Command frame TODO: Implement receive_all()
            # cfg1_frame = sock.recv(2048)
            #
            # # TODO: validate Configuration Frame
            # self.source_cfg1 = cfg1_frame
            # self.logger.info("[%s] - Received Configuration frame 1 from %s:%d", self.name, self.source_ip,
            #                  self.source_port)

            # Get Configuration frame 2 from PMU
            self.logger.info("[%s] - Requesting Configuration frame 2 from %s:%d", self.name, self.source_ip,
                             self.source_port)
            cfg = CommandFrame(self.id, 'cfg2')
            sock.sendall(cfg.convert2bytes())

            # Wait for Command frame TODO: Implement receive_all()
            cfg2_frame = sock.recv(self.buffer_size)

            # TODO: validate Configuration Frame
            self.source_cfg2 = cfg2_frame
            self.logger.info("[%s] - Received Configuration frame 2 from %s:%d", self.name, self.source_ip,
                             self.source_port)

            # # Get Configuration frame 3 from PMU
            # self.logger.info("[%s] - Requesting Configuration frame 3 from %s:%d", self.name, self.source_ip,
            #                  self.source_port)
            # cfg = CommandFrame(self.id, 'cfg3')
            # sock.sendall(cfg.convert2bytes())
            #
            # # Wait for Command frame TODO: Implement receive_all()
            # cfg3_frame = sock.recv(2048)
            #
            # # TODO: validate Configuration Frame
            # self.source_cfg2 = cfg3_frame
            # self.logger.info("[%s] - Received Configuration frame 3 from %s:%d", self.name, self.source_ip,
            #                  self.source_port)

            # Request to start sending
            self.logger.info("[%s] - Request to start sending data from %s:%d", self.name, self.source_ip,
                             self.source_port)
            start = CommandFrame(self.id, 'start')
            sock.sendall(start.convert2bytes())

            # Keep receiving data and pass it to connected PMUs (clients)
            while True:

                data = sock.recv(2048)  # TODO: Implement receive_all()
                if data:  # TODO: Refactor this to use get_frame() and pass to FrameTranslator
                    try:
                        # Try to get get message type:
                        frame_type = CommonFrame.extract_frame_type(data)

                        if frame_type == 'cfg1':
                            self.source_cfg1 = data
                            self.logger.info("[%s] - Received Configuration frame 1", self.name, self.source_ip,
                                             self.source_port)

                        elif frame_type == 'cfg2':
                            self.source_cfg2 = data
                            self.logger.info("[%s] - Received Configuration frame 2", self.name, self.source_ip,
                                             self.source_port)

                        elif frame_type == 'cfg3':
                            self.source_cfg3 = data
                            self.logger.info("[%s] - Received Configuration frame 2", self.name, self.source_ip,
                                             self.source_port)

                        elif frame_type == 'header':
                            self.source_header = data
                            self.logger.info("[%s] - Received Header frame", self.name, self.source_ip,
                                             self.source_port)
                    except Exception:
                        self.logger.warning("[%s] - Received unknown message", self.name)

                    for buffer in self.client_buffers:
                        buffer.put(data)
                else:
                    break
        finally:
            self.logger.info("[%s] - Closing source socket at %s:%d", self.name, self.source_ip, self.source_port)
            sock.close()

    def __init__(self, source_ip, source_port, listen_ip, listen_port, pdc_id=1, method='tcp', buffer_size=2048):

        self.socket = None
        self.listener = None
        self.buffer_size = buffer_size

        self.source_ip = source_ip
        self.source_port = source_port
        self.listen_ip = listen_ip
        self.listen_port = listen_port

        self.id = pdc_id
        self.method = method
        self.name = 'Splitter - (' + source_ip + ':' + str(source_port) + ')'

        self.source_cfg1 = None
        self.source_cfg2 = None
        self.source_cfg3 = None
        self.source_header = None

        self.client_buffers = []


class StreamSplitterError(BaseException):
    pass
