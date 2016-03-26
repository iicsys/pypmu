#!/usr/bin/env python3

from argparse import ArgumentParser
from synchrophasor.splitter import StreamSplitter

"""
splytter - will pass source data stream to each connected PDC.
Variables source_ip and source_port represent data stream source
(PMU or PDC). StreamSplitter will listen on  listen_ip and
listen_port for incoming connections from PDCs.
"""

__author__ = "Stevan Sandi"
__copyright__ = "Copyright (c) 2016, Tomo Popovic, Stevan Sandi, Bozo Krstajic"
__credits__ = []
__license__ = "GPL"
__version__ = "1.0"

argument_parser = ArgumentParser(description='splytter - replicate data stream to many PDCs.')
argument_parser.add_argument('-si', '--source_ip', help='Data stream source IP.', required=True)
argument_parser.add_argument('-sp', '--source_port', help='Data stream source port.', required=True, type=int)
argument_parser.add_argument('-li', '--listen_ip', help='splytter - listen IP.', required=True)
argument_parser.add_argument('-lp', '--listen_port', help='splytter - listen port.', required=True, type=int)
argument_parser.add_argument('-i', '--id', help='splytter - ID code as PDC.', default=1, type=int)
argument_parser.add_argument('-m', '--method', help='Transmission method TCP or UDP.',
                             choices=['tcp', 'udp'], default='tcp')
argument_parser.add_argument('-b', '--buffer', help='Transmission method buffer size.', default=2048, type=int)
arguments = argument_parser.parse_args()

sp = StreamSplitter(arguments.source_ip, arguments.source_port, arguments.listen_ip, arguments.listen_port,
                    arguments.id, arguments.method, arguments.buffer)

print("[ INFO ] Connecting to %s:%d with ID: %d.", arguments.source_ip, arguments.source_port)
print("[ INFO ] Listening on %s:%d for incoming connections.", arguments.listen_ip, arguments.listen_port)
print("[ INFO ] Using %s method with buffer size: %d", arguments.method, arguments.buffer)
print("-----------------------------------------------------")

sp.run()
sp.join()
