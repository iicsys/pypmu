import multiprocessing
import threading
import socket
import logging

from synchrophasor.frame import *
from sys import stdout
from select import select
from time import sleep
from time import time

__author__ = "Stevan Sandi"
__copyright__ = "Copyright (c) 2016, Tomo Popovic, Stevan Sandi, Bozo Krstajic"
__credits__ = []
__license__ = "BSD-3"
__version__ = "0.1.1"


class Pmu(object):

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    def pmu_handler(self, connection, address, buffer):

        self.logger.info("[%d] - Connection from %s:%d", self.pmu_id, address[0], address[1])

        # Wait for start command from connected PDC/PMU to start sending
        sending_measurements_enabled = False

        # Calculate delay between data frames
        if self.data_rate > 0:
            delay = 1.0 / self.data_rate
        else:
            delay = self.data_rate

        try:
            while True:

                command = None
                received_data = b''
                readable, writable, exceptional = select([connection], [], [], 0)  # Check for client commands

                if readable:
                    """
                    Keep receiving until SYNC + FRAMESIZE is received, 4 bytes in total.
                    Should get this in first iteration. FRAMESIZE is needed to determine when one complete message
                    has been received.
                    """
                    while len(received_data) < 4:
                        received_data += connection.recv(self.buffer_size)

                    bytes_received = len(received_data)
                    total_frame_size = pmu_code = int.from_bytes(received_data[2:4], byteorder='big', signed=False)

                    # Keep receiving until every byte of that message is received
                    while bytes_received < total_frame_size:
                        message_chunk = connection.recv(min(total_frame_size - bytes_received, self.buffer_size))
                        if not message_chunk:
                            break
                        received_data.append(message_chunk)
                        bytes_received += len(message_chunk)

                    # If complete message is received try to decode it
                    if len(received_data) == total_frame_size:
                        try:
                            received_message = CommonFrame.convert2frame(received_data)  # Try to decode received data

                            self.logger.info("[%d] - Received command: [%s] <- (%s:%d)", self.pmu_id, command,
                                                 address[0], address[1])
                            if isinstance(received_message, CommandFrame):
                                command = received_message.get_command()
                                self.logger.info("[%d] - Received command: [%s] <- (%s:%d)", self.pmu_id, command,
                                                 address[0], address[1])
                            else:
                                self.logger.info("[%d] - Received %s: [%s] <- (%s:%d)", type(received_message).__name__,
                                                 self.pmu_id, command, address[0], address[1])
                        except FrameError:
                            self.logger.warning("[%d] - Received unknown message <- (%s:%d)", self.pmu_id,
                                                address[0], address[1])
                    else:
                        self.logger.warning("[%d] - Message not received completely <- (%s:%d)", self.pmu_id,
                                            address[0], address[1])

                if command == 'start':
                    sending_measurements_enabled = True
                    self.logger.info("[%d] - Start sending -> (%s:%d)", self.pmu_id, address[0], address[1])

                elif command == 'stop':
                    self.logger.info("[%d] - Stop sending -> (%s:%d)", self.pmu_id, address[0], address[1])
                    sending_measurements_enabled = False

                elif command == 'header':
                    connection.sendall(self.header.convert2bytes())
                    self.logger.info("[%d] - Requested Header frame sent -> (%s:%d)",
                                     self.pmu_id, address[0], address[1])
                elif command == 'cfg1':
                    connection.sendall(self.cfg1.convert2bytes())
                    self.logger.info("[%d] - Requested Configuration frame 1 sent -> (%s:%d)", self.pmu_id,
                                     address[0], address[1])
                elif command == 'cfg2':
                    connection.sendall(self.cfg2.convert2bytes())
                    self.logger.info("[%d] - Requested Configuration frame 2 sent -> (%s:%d)", self.pmu_id,
                                     address[0], address[1])
                elif command == 'cfg3':
                    connection.sendall(self.cfg3.convert2bytes())
                    self.logger.info("[%d] - Requested Configuration frame 3 sent -> (%s:%d)", self.pmu_id,
                                     address[0], address[1])

                if sending_measurements_enabled and not buffer.empty():
                    sleep(delay)
                    connection.sendall(buffer.get())
                    self.logger.debug("[%d] - Message sent at [%f] -> (%s:%d)", self.pmu_id, time(), address[0],
                                      address[1])  # TODO: Remove this for better performance

        except Exception as e:
            print(e)
        finally:
            connection.close()
            self.client_buffers.remove(buffer)
            self.logger.info("[%d] - Connection from %s:%d has been closed.", self.pmu_id, address[0], address[1])

    def join(self):
        # threading.Thread.join() is not interruptible, so tight loop in a sleep-based join
        while self.listener.is_alive():
            self.listener.join(0.5)

    def acceptor(self):
        while True:
            self.logger.info("[%d] - Waiting for connection on %s:%d", self.pmu_id, self.ip, self.port)

            # Accept a connection on the bound socket and fork a child process to handle it.
            conn, address = self.socket.accept()

            # Create Queue which will represent buffer for specific client and add it o list of all client buffers
            buffer = multiprocessing.Queue()
            self.client_buffers.append(buffer)

            process = multiprocessing.Process(
                target=self.pmu_handler, args=(conn, address, buffer))
            process.daemon = True
            process.start()
            self.clients.append(process)

            # Close the connection fd in the parent, since the child process has its own reference.
            conn.close()

    def __init__(self, pmu_id=7734, data_rate=30, port=4712, ip='127.0.0.1', method='tcp', buffer_size=2048):

        self.port = port
        self.ip = ip

        self.socket = None
        self.listener = None
        self.buffer_size = buffer_size

        self.ieee_cfg2_sample = ConfigFrame2(7734, 1000000, 1, "Station A", 7734, (False, False, True, False), 4, 3, 1,
                                             ["VA", "VB", "VC", "I1", "ANALOG1", "ANALOG2", "ANALOG3",
                                              "BREAKER 1 STATUS", "BREAKER 2 STATUS", "BREAKER 3 STATUS",
                                              "BREAKER 4 STATUS", "BREAKER 5 STATUS", "BREAKER 6 STATUS",
                                              "BREAKER 7 STATUS", "BREAKER 8 STATUS", "BREAKER 9 STATUS",
                                              "BREAKER A STATUS", "BREAKER B STATUS", "BREAKER C STATUS",
                                              "BREAKER D STATUS", "BREAKER E STATUS", "BREAKER F STATUS",
                                              "BREAKER G STATUS"],
                                             [(915527, 'v'), (915527, 'v'), (915527, 'v'), (45776, 'i')],
                                             [(1, 'pow'), (1, 'rms'), (1, 'peak')], [(0x0000, 0xffff)], 60, 22, 30)

        self.ieee_data_sample = DataFrame(7734, ('ok', True, 'timestamp', False, False, False, 0, '<10', 0),
                                          [(14635, 0), (58218, 52860), (58218, 12675), (1092, 0)], 2500, 0,
                                          [100, 1000, 10000], [0x3c12], 0x0004)

        self.ieee_command_sample = CommandFrame(7734, 'start', None)

        self.cfg1 = None
        self.cfg2 = self.ieee_cfg2_sample
        self.cfg3 = None
        self.header = HeaderFrame(pmu_id, 'Hi! I am tinyPMU!')

        self.pmu_id = pmu_id
        self.data_rate = data_rate
        self.num_pmu = self.cfg2.num_pmu
        self.data_format = self.cfg2.data_format
        self.method = method

        self.clients = []
        self.client_buffers = []

    def run(self):

        if not self.cfg1 and not self.cfg2 and not self.cfg3:
            raise PmuError('Cannot run PMU without configuration.')

        # Create TCP socket, bind port and listen for incoming connections
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.ip, self.port))
        self.socket.listen(5)

        self.listener = threading.Thread(target=self.acceptor)  # Run acceptor thread to handle new connection
        self.listener.daemon = True
        self.listener.start()

    def set_configuration(self, conifg=None):

        # If none configuration given IEEE sample configuration will be loaded
        if not conifg:
            self.cfg1 = None  # TODO: Configuration frame 1
            self.cfg2 = self.ieee_cfg2_sample
            self.cfg3 = None  # TODO: Configuration frame 3

        elif isinstance(conifg, ConfigFrame1):
            self.cfg1 = conifg
            self.cfg2 = None  # TODO: Use ConfigFrame1 to create ConfigFrame2 if possible
            self.cfg3 = None  # TODO: Use ConfigFrame1 to create ConfigFrame3 if possible

        elif isinstance(conifg, ConfigFrame2):
            self.cfg1 = None  # TODO: Use ConfigFrame2 to create ConfigFrame1 if possible
            self.cfg2 = conifg
            self.cfg3 = None  # TODO: Use ConfigureFrame2 to create ConfigFrame3 if possible

        elif isinstance(conifg, ConfigFrame3):
            self.cfg1 = None  # TODO: Use ConfigFrame3 to create ConfigFrame1 if possible
            self.cfg2 = None  # TODO: Use ConfigFrame3 to create ConfigFrame2 if possible
            self.cfg3 = ConfigFrame3

        else:
            raise PmuError('Incorrect configuration!')

        # Update data rate and PMU ID if changed:
        if conifg:
            self.pmu_id = conifg.pmu_id_code
            self.data_rate = conifg.data_rate
            self.data_format = conifg.data_format
            self.num_pmu = conifg.num_pmu
        else:
            self.pmu_id = self.ieee_cfg2_sample.pmu_id_code
            self.data_rate = self.ieee_cfg2_sample.data_rate
            self.data_format = self.ieee_cfg2_sample.data_format
            self.num_pmu = self.ieee_cfg2_sample.num_pmu

        # self.send(self.cfg1)
        self.send(self.cfg2)
        # self.send(self.cfg3)

        self.logger.info("[%d] - PMU configuration changed.", self.pmu_id)

    def set_header(self, header=None):

        if isinstance(header, HeaderFrame):
            self.header = header
        elif isinstance(header, str):
            self.header.header = header
        else:
            PmuError('Incorrect header setup! Only HeaderFrame and string allowed.')

        # Notify all connected PDCs about new header
        self.send(self.header)

        self.logger.info("[%d] - PMU header changed.", self.pmu_id)

    def set_id(self, pmu_id):

        # self.cfg1.set_id_code(id)
        self.cfg2.set_id_code(pmu_id)
        # self.cfg3.set_id_code(id)
        self.pmu_id = pmu_id

        # Configuration changed - Notify all PDCs about new configuration
        # self.send(self.cfg1)
        self.send(self.cfg2)
        # self.send(self.cfg3)

        self.logger.info("[%d] - PMU Id changed.", self.pmu_id)

    def set_data_rate(self, data_rate):

        # self.cfg1.set_data_rate(data_rate)
        self.cfg2.set_data_rate(data_rate)
        # self.cfg3.set_data_rate(data_rate)
        self.data_rate = data_rate

        # Configuration changed - Notify all PDCs about new configuration
        # self.send(self.cfg1)
        self.send(self.cfg2)
        # self.send(self.cfg3)

        self.logger.info("[%d] - PMU reporting data rate changed.", self.pmu_id)

    def set_data_format(self, data_format):

        self.cfg1.set_data_format(data_format, self.cfg1.num_pmu)
        self.cfg2.set_data_format(data_format, self.cfg2.num_pmu)
        self.cfg3.set_data_format(data_format, self.cfg3.num_pmu)
        self.data_format = data_format

        # Configuration changed - Notify all PDCs about new configuration
        # self.send(self.cfg1)
        self.send(self.cfg2)
        # self.send(self.cfg3)

        self.logger.info("[%d] - PMU data format changed.", self.pmu_id)

    def send(self, frame, set_timestamp=True):

        if isinstance(frame, CommonFrame):
            if set_timestamp:
                frame.set_time()

            data = frame.convert2bytes()

        elif isinstance(frame, bytes):
            data = frame

        else:
            raise PmuError('Invalid frame type. send() method accepts only frames or raw bytes.')

        for buffer in self.client_buffers:
            buffer.put(data)

    def send_data(self, phasors=[], analog=[], digital=[], freq=0, dfreq=0,
                  stat=('ok', True, 'timestamp', False, False, False, 0, '<10', 0), soc=None, frasec=None):

        # PH_UNIT conversion
        if phasors and self.num_pmu > 1:  # Check if multistreaming:
            if not (self.num_pmu == len(self.data_format) == len(phasors)):
                raise PmuError('Incorrect input. Please provide PHASORS as list of lists with NUM_PMU elements.')

            for i, df in self.data_format:  # TODO: Are you really going to check data format like this?
                if df in [0, 1, 4, 5, 8, 12, 13]:  # Check if phasor representation is integer
                    phasors[i] = map(lambda x: int(x/(0.00001*self.cfg2.ph_units[i])), phasors[i])
        elif self.data_format in [0, 1, 4, 5, 8, 12, 13]:
            phasors = map(lambda x: int(x/(0.00001*self.cfg2.ph_units)), phasors)

        # AN_UNIT conversion
        if analog and self.num_pmu > 1:  # Check if multistreaming:
            if not (self.num_pmu == len(self.data_format) == len(analog)):
                raise PmuError('Incorrect input. Please provide analog ANALOG as list of lists with NUM_PMU elements.')

            for i, df in self.data_format:  # TODO: Are you really going to check data format like this?
                if df in [0, 1, 2, 3, 8, 9, 10]:  # Check if analog representation is integer
                    analog[i] = map(lambda x: int(x/self.cfg2.an_units[i]), analog[i])
        elif self.data_format in [0, 1, 2, 3, 8, 9, 10]:
            analog = map(lambda x: int(x/self.cfg2.an_units), analog)

        data_frame = DataFrame(self.pmu_id, stat, phasors, freq, dfreq, analog, digital,
                               self.data_format, self.num_pmu)

        if not soc and not frasec:
            data_frame.set_time()

        for buffer in self.client_buffers:
            buffer.put(data_frame.convert2bytes())


class PmuError(BaseException):
    pass
