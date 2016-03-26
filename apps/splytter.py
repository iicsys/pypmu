from synchrophasor.splitter import StreamSplitter

"""
StreamSplitter will pass source data stream to each connected PDC.
Variables source_ip and source_port represent data stream source
(PMU or PDC). StreamSplitter will listen on  listen_ip and
listen_port for incoming connections from PDCs.
"""

sp = StreamSplitter(source_ip='127.0.0.1', source_port=1410, listen_ip='127.0.0.1', listen_port=1502)

sp.run()
sp.join()
