import logging
import socket
import struct
import sys
from sys import stdout
from synchrophasor.frame import *


__author__ = "Stevan Sandi"
__copyright__ = "Copyright (c) 2016, Tomo Popovic, Stevan Sandi, Bozo Krstajic"
__credits__ = []
__license__ = "BSD-3"
__version__ = "1.0.0-alpha"


class Pdc(object):

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(stdout)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    def __init__(self, pdc_id=1, pmu_ip="127.0.0.1", pmu_port=4712, buffer_size=2048, method="tcp", config2=None):

        self.pdc_id = pdc_id
        self.buffer_size = buffer_size
        self.method = method

        self.pmu_ip = pmu_ip
        self.pmu_port = pmu_port
        self.pmu_address = (pmu_ip, pmu_port)
        self.pmu_socket = None
        self.pmu_cfg1 = None

        #self.pmu_cfg2 = None
        self.pmu_cfg2 = config2

        self.pmu_header = None

    def get_cfg2(self, config2):
        return self.pmu_cfg2

    def set_cfg2(self, config2):
        self.pmu_cfg2 = config2

    def run(self):

        if self.pmu_socket:
            self.logger.info("[%d] - PDC already connected to PMU (%s:%d)",
                             self.pdc_id, self.pmu_ip, self.pmu_port)
        else:
            try:
                # Connect to PMU
                if(self.method == "tcp"):
                    self.pmu_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.pmu_socket.connect(self.pmu_address)
                    self.logger.info("[%d] - PDC successfully connected to PMU (%s:%d)as %s",
                                     self.pdc_id, self.pmu_ip, self.pmu_port, self.method)
                if(self.method == "udp"):
                    self.pmu_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    # self.pmu_socket.connect(self.pmu_address)
                    self.pmu_socket.bind(('', self.pmu_port))
                    self.logger.info("[%d] - PDC successfully connected to PMU (%s:%d) as %s",
                                     self.pdc_id, self.pmu_ip, self.pmu_port, self.method)
                if(self.method == "multicast"):
                    self.pmu_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self.pmu_socket.bind(('', self.pmu_port))
                    self.pmu_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, struct.pack(
                        '4sL', socket.inet_aton(self.pmu_ip), socket.INADDR_ANY))
                    self.logger.info("[%d] - PDC successfully connected to PMU (%s:%d) as %s",
                                     self.pdc_id, self.pmu_ip, self.pmu_port, self.method)
            except Exception as e:
                self.logger.error("[%d] - Error while connecting to (%s:%d)",
                                  self.pdc_id, self.pmu_ip, self.pmu_port)
                self.logger.error(str(e))

    def start(self):
        """
        Request from PMU to start sending data
        :return: NoneType
        """
        start = CommandFrame(self.pdc_id, "start")
        if(self.method == "tcp"):
            self.pmu_socket.sendall(start.convert2bytes())
        else:
            self.pmu_socket.sendto(start.convert2bytes(), (self.pmu_ip, self.pmu_port))
        self.logger.info("[%d] - Requesting to start sending from PMU (%s:%d)",
                         self.pdc_id, self.pmu_ip, self.pmu_port)

    def stop(self):
        """
        Request from PMU to start sending data
        :return: NoneType
        """
        if(self.method == "tcp"):
            start = CommandFrame(self.pdc_id, "stop")
            self.pmu_socket.sendall(start.convert2bytes())
            self.logger.info("[%d] - Requesting to stop sending from PMU (%s:%d)",
                             self.pdc_id, self.pmu_ip, self.pmu_port)
        else:
            start = CommandFrame(self.pdc_id, "stop")
            self.pmu_socket.sendto(start.convert2bytes(), self.pmu_address)
            self.logger.info("[%d] - Requesting to stop sending from PMU (%s:%d)",
                             self.pdc_id, self.pmu_ip, self.pmu_port)

    def get_header(self):
        """
        Request for PMU header message
        :return: HeaderFrame
        """
        get_header = CommandFrame(self.pdc_id, "header")
        self.pmu_socket.sendall(get_header.convert2bytes())

        self.logger.info("[%d] - Requesting header message from PMU (%s:%d)",
                         self.pdc_id, self.pmu_ip, self.pmu_port)

        header = self.get()
        if isinstance(header, HeaderFrame):
            return header
        else:
            raise PdcError("Invalid Header message received")

    def get_config(self, version="cfg2"):
        """
        Request for Configuration frame.
        :param version: string Possible values "cfg1", "cfg2" and "cfg3"
        :return: ConfigFrame
        """
        get_config = CommandFrame(self.pdc_id, version)

        if(self.method == "udp"):
            self.pmu_socket.sendto(get_config.convert2bytes(), self.pmu_address)
            config = self.get()
            if type(config) == ConfigFrame1:
                self.pmu_cfg1 = config
            elif type(config) == ConfigFrame2:
                self.pmu_cfg2 = config
            return config
        else:
            self.pmu_socket.sendall(get_config.convert2bytes())

            config = self.get()
            if type(config) == ConfigFrame1:
                self.pmu_cfg1 = config
            elif type(config) == ConfigFrame2:
                self.pmu_cfg2 = config
            else:
                raise PdcError("Invalid Configuration message received")

            return config

    def get(self):
        """
        Decoding received messages from PMU
        :return: CommonFrame
        """

        received_data = b""
        received_message = None

        """
        Keep receiving until SYNC + FRAMESIZE is received, 4 bytes in total.
        Should get this in first iteration. FRAMESIZE is needed to determine when one complete message
        has been received.
        """
        # Keep receiving until every byte of that message is received
        if(self.method == "tcp"):

            received_data += self.pmu_socket.recv(4)
            bytes_received = len(received_data)
            total_frame_size = int.from_bytes(received_data[2:4], byteorder="big", signed=False)
            # print(total_frame_size)
            while bytes_received < total_frame_size:
                message_chunk = self.pmu_socket.recv(
                    min(total_frame_size - bytes_received, self.buffer_size))
                if not message_chunk:
                    break
                received_data += message_chunk
                bytes_received += len(message_chunk)

        if((self.method == "udp") or (self.method == "multicast")):
            received_data = self.pmu_socket.recv(1024)
            total_frame_size = int.from_bytes(received_data[2:4], byteorder="big", signed=False)
            # print(received_data)
        # If complete message is received try to decode it
        if len(received_data) == total_frame_size:
            # print(self.pmu_cfg2)
            try:
                received_message = CommonFrame.convert2frame(
                    received_data, self.pmu_cfg2)  # Try to decode received data
                #self.logger.debug("[%d] - Received %s from PMU (%s:%d)", self.pdc_id, type(received_message).__name__,self.pmu_ip, self.pmu_port)
            except FrameError:
                self.logger.warning("[%d] - Received unknown message from PMU (%s:%d)",
                                    self.pdc_id, self.pmu_ip, self.pmu_port)

        return received_message

    def quit(self):
        """
        Close connection to PMU
        :return: NoneType
        """
        self.pmu_socket.close()
        self.logger.info("[%d] - Connection to PMU closed (%s:%d)",
                         self.pdc_id, self.pmu_ip, self.pmu_port)


class PdcError(BaseException):
    pass
