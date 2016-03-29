import logging
import socket

from sys import stdout
from synchrophasor.frame import *

__author__ = "Stevan Sandi"
__copyright__ = "Copyright (c) 2016, Tomo Popovic, Stevan Sandi, Bozo Krstajic"
__credits__ = []
__license__ = "GPL"
__version__ = "1.0"


class Pdc(object):

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    def __init__(self, pdc_id=1, pmu_ip='127.0.0.1', pmu_port=4712, buffer_size=2048, method='tcp'):

        self.pdc_id = pdc_id
        self.buffer_size = buffer_size
        self.method = method

        self.pmu_ip = pmu_ip
        self.pmu_port = pmu_port
        self.pmu_address = (pmu_ip, pmu_port)
        self.pmu_socket = None

    def run(self):

        if self.pmu_socket:
            self.logger.info("[%d] - PDC already connected to PMU (%s:%d)", self.pdc_id, self.pmu_ip, self.pmu_port)
        else:
            try:
                # Connect to PMU
                self.pmu_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.pmu_socket.connect(self.pmu_address)
                self.logger.info("[%d] - PDC successfully connected to PMU (%s:%d)",
                                 self.pdc_id, self.pmu_ip, self.pmu_port)
            except Exception as e:
                self.logger.error("[%d] - Error while connecting to (%s:%d)", self.pdc_id, self.pmu_ip, self.pmu_port)
                self.logger.error(str(e))

    def start(self):
        """
        Request from PMU to start sending data
        :return: NoneType
        """
        start = CommandFrame(self.pdc_id, 'start')
        self.pmu_socket.sendall(start.convert2bytes())
        self.logger.info("[%d] - Requesting to start sending from PMU (%s:%d)", self.pdc_id, self.pmu_ip, self.pmu_port)

    def stop(self):
        """
        Request from PMU to start sending data
        :return: NoneType
        """
        start = CommandFrame(self.pdc_id, 'stop')
        self.pmu_socket.sendall(start.convert2bytes())
        self.logger.info("[%d] - Requesting to stop sending from PMU (%s:%d)", self.pdc_id, self.pmu_ip, self.pmu_port)

    def get_header(self):
        """
        Request for PMU header message
        :return: HeaderFrame
        """
        get_header = CommandFrame(self.pdc_id, 'header')
        self.pmu_socket.sendall(get_header.convert2bytes())

        self.logger.info("[%d] - Requesting header message from PMU (%s:%d)", self.pdc_id, self.pmu_ip, self.pmu_port)

        header = self.get()
        if isinstance(header, HeaderFrame):
            return header
        else:
            return None

    def get_config(self, version='cfg2'):
        """
        Request for Configuration frame.
        :param version: string Possible values 'cfg1', 'cfg2' and 'cfg3'
        :return: ConfigFrame
        """
        get_config = CommandFrame(self.pdc_id, version)
        self.pmu_socket.sendall(get_config.convert2bytes())

        config = self.get()
        if isinstance(config, ConfigFrame):
            return config
        else:
            return None

    def get(self):
        """
        Decoding received messages from PMU
        :return: CommonFrame
        """

        data = self.pmu_socket.recv(self.buffer_size)  # TODO: implement recv_all()
        received_message = None
        if data:
            try:
                received_message = CommonFrame.convert2frame(data)  # Try to decode received data

                if isinstance(received_message, DataFrame):
                    self.logger.debug("[%d] - Received measurement from PMU (%s:%d)",
                                      self.pdc_id, self.pmu_ip, self.pmu_port)
                elif isinstance(received_message, ConfigFrame):
                    self.logger.debug("[%d] - Received configuration from PMU (%s:%d)",
                                      self.pdc_id, self.pmu_ip, self.pmu_port)
                elif isinstance(received_message, HeaderFrame):
                    self.logger.debug("[%d] - Received header message from PMU (%s:%d)",
                                      self.pdc_id, self.pmu_ip, self.pmu_port)
                elif isinstance(received_message, CommandFrame):
                    self.logger.debug("[%d] - Received command from PMU (%s:%d)",
                                      self.pdc_id, self.pmu_ip, self.pmu_port)
                else:
                    self.logger.debug("[%d] - Whooa! Whooa! I don't know what is this :( Please implement "
                                      "convert2frame() methods (%s:%d)", self.pdc_id, self.pmu_ip, self.pmu_port)
            except FrameError:
                received_message = None
                self.logger.warning("[%d] - Received unknown message from PMU (%s:%d)",
                                    self.pdc_id, self.pmu_ip, self.pmu_port)

        return received_message

    def quit(self):
        """
        Close connection to PMU
        :return: NoneType
        """
        self.pmu_socket.close()
        self.logger.info("[%d] - Connection to PMU closed (%s:%d)", self.pdc_id, self.pmu_ip, self.pmu_port)


class PdcError(BaseException):
    pass
