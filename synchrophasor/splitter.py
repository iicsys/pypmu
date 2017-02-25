from synchrophasor.frame import *
from synchrophasor.pdc import Pdc
from synchrophasor.pmu import Pmu


__author__ = "Stevan Sandi"
__copyright__ = "Copyright (c) 2016, Tomo Popovic, Stevan Sandi, Bozo Krstajic"
__credits__ = []
__license__ = "BSD-3"
__version__ = "1.0.0-aplha"


class StreamSplitter(object):

    def __init__(self, source_ip, source_port, listen_ip, listen_port, pdc_id=1, method="tcp", buffer_size=2048):

        self.pdc = Pdc(pdc_id, source_ip, source_port, buffer_size, method)
        self.pmu = Pmu(ip=listen_ip, port=listen_port, method=method, buffer_size=buffer_size, set_timestamp=False)

        self.source_cfg1 = None
        self.source_cfg2 = None
        self.source_cfg3 = None
        self.source_header = None


    def run(self):

        self.pdc.run()
        self.source_header = self.pdc.get_header()
        self.source_cfg2 = self.pdc.get_config()
        self.pdc.start()

        self.pmu.run()
        self.pmu.set_header(self.source_header)
        self.pmu.set_configuration(self.source_cfg2)

        while True:

            message = self.pdc.get()

            if self.pmu.clients and message:

                self.pmu.send(message)

                if isinstance(message, HeaderFrame):
                    self.pmu.set_header(message)
                elif isinstance(message, ConfigFrame2):
                    self.pmu.set_configuration(message)


class StreamSplitterError(BaseException):
    pass
