from synchrophasor.pdc import Pdc

"""
tinyPDC will connect to pmu_ip:pmu_port and send request
for header message, configuration and eventually
to start sending measurements.
"""

pdc = Pdc(pdc_id=7, pmu_ip='127.0.0.1', pmu_port=1410)

pdc.run()  # Connect to PMU

header = pdc.get_header()  # Get header message from PMU
config = pdc.get_config()  # Get configuration from PMU

pdc.start()  # Request to start sending measurements

while True:
    data = pdc.get()  # Keep receiving data
    if not data:
        pdc.quit()  # Close connection
        break
