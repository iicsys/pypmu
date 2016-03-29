import time
import datetime
import os

from synchrophasor.pdc import Pdc
from synchrophasor.frame import FrameError
from argparse import ArgumentParser


argument_parser = ArgumentParser(description='benchPDC - will connect to given PDC'
                                             'Usage example: '
                                             './behchPDC.py -i 511 -ip 127.0.0.1 -p 1995 -r 30')

argument_parser.add_argument('-i', '--id', help='PDC ID code.', default=7734, type=int)
argument_parser.add_argument('-ip', '--ip', help='PMU IP.', required=True)
argument_parser.add_argument('-p', '--port', help='PMU port.', required=True, type=int)
argument_parser.add_argument('-r', '--data_rate', help='Data reporting rate of the PMU.', default=30, type=int)
argument_parser.add_argument('-j', '--jobs', help='How many jobs in parallel.', default=1, type=int)
argument_parser.add_argument('-m', '--method', help='Transmission method TCP or UDP.',
                             choices=['tcp', 'udp'], default='tcp')
argument_parser.add_argument('-b', '--buffer', help='Transmission method buffer size.', default=2048, type=int)
arguments = argument_parser.parse_args()

pdc = Pdc(pdc_id=arguments.id, pmu_ip=arguments.ip, pmu_port=arguments.port,
          buffer_size=arguments.buffer, method=arguments.method)

pdc.run()  # Connect to PMU

header = pdc.get_header()  # Get header message from PMU
config = pdc.get_config()  # Get configuration from PMU

# Receive ideal number of measurements in 60s.
measurements2receive = 60 * arguments.data_rate
timestamp = datetime.now().strftime('%Y%m%d_%H:%M:%S')
errors = 0

# Create result folder
if not os.path.exists('results'):
    os.makedirs('results')

log = "./results/result_{:d}_{:d}_{:d}_{:s}.log".format(arguments.data_rate, arguments.jobs, arguments.id, timestamp)

pdc.start()  # Request to start sending measurements
start_time = stop_time = time.time()
while measurements2receive > 0:
    try:
        data = pdc.get()  # Keep receiving data
    except FrameError:
        errors += 1

    if measurements2receive == 1:
        stop_time = time.time()

    if not data:
        pdc.quit()  # Close connection
        break

    measurements2receive -= 1

# Write results to file:
with open(log, 'w') as log_file:
    log_file.write("PDC ID: {:d}\n".format(arguments.id))
    log_file.write("Result: {:f}\n".format(stop_time-start_time))
    log_file.write("Errors: {:d}\n".format(errors))
