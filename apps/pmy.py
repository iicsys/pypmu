#!/usr/bin/env python3

from argparse import ArgumentParser
from synchrophasor.pmu import Pmu


"""
pmy - will listen on ip:port for incoming connections.
When tinyPMU receives command to start sending
measurements - fixed (sample) measurement will
be sent.
"""

__author__ = "Stevan Sandi"
__copyright__ = "Copyright (c) 2016, Tomo Popovic, Stevan Sandi, Bozo Krstajic"
__credits__ = []
__license__ = "BSD-3"
__version__ = "1.0.0-alpha"


if __name__ == "__main__":

    argument_parser = ArgumentParser(description="pmy - PMU simulator, sending constant sample measurement. "
                                                 "Usage example: "
                                                 "./pmy.py -i 511 -ip 127.0.0.1 -p 1995 -r 30")

    argument_parser.add_argument("-i", "--id", help="PMU ID code.", default=7734, type=int)
    argument_parser.add_argument("-ip", "--ip", help="Listener IP.", required=True)
    argument_parser.add_argument("-p", "--port", help="Listener port.", required=True, type=int)
    argument_parser.add_argument("-r", "--data_rate", help="Data reporting rate.", default=30, type=int)
    argument_parser.add_argument("-t", "--timestamp", help="Set timestamp for each frame.", action="store_true")
    argument_parser.add_argument("-m", "--method", help="Transmission method TCP or UDP.",
                                 choices=["tcp", "udp"], default="tcp")
    argument_parser.add_argument("-b", "--buffer", help="Transmission method buffer size.", default=2048, type=int)
    argument_parser.add_argument("-l", "--log_level", help="Log level.",
                                 choices=["CRITICAL", "ERROR", "WARN", "WARNING", "INFO", "DEBUG", "NOTSET"],
                                 default="INFO")

    arguments = argument_parser.parse_args()

    pmu = Pmu(arguments.id, arguments.data_rate, arguments.port, arguments.ip, 
              arguments.method, arguments.buffer, arguments.timestamp)
    pmu.logger.setLevel(arguments.log_level)

    pmu.set_configuration()  # This will load default PMU configuration specified in IEEE C37.118.2 - Annex D (Table D.2)
    pmu.set_header()  # This will load default header message "Hello I'm tinyPMU!"

    pmu.set_id(arguments.id)  # Override PMU ID set by set_configuration method.
    pmu.set_data_rate(arguments.data_rate)  # Override reporting DATA_RATE set by set_configuration method.

    pmu.run()  # PMU starts listening for incoming connections

    while True:
        if pmu.clients:  # Check if there is any connected PDCs
            pmu.send(pmu.ieee_data_sample)  # Sending sample data frame specified in IEEE C37.118.2 - Annex D (Table D.1)

    pmu.join()
