import binascii
from synchrophasor.frame import DataFrame
from synchrophasor.frame import ConfigFrame2
from synchrophasor.frame import HeaderFrame
from synchrophasor.frame import CommandFrame

__author__ = "Stevan Sandi"
__copyright__ = "Copyright (c) 2016, Tomo Popovic, Stevan Sandi, Bozo Krstajic"
__credits__ = []
__license__ = "BSD-3"
__version__ = "0.1"


data_hex_string = 'aa0100341e3644853600000041b10000392b0000e36ace7ce36a31830444000009c4000042c80000447a0000461c4000' \
                  '3c12d43f'

df = DataFrame(7734, ('ok', True, 'timestamp', False, False, False, 0, '<10', 0),
               [(14635,  0), (58218, 52860), (58218, 12675), (1092, 0)], 2500, 0, [100, 1000, 10000], [0x3c12], 0x0004,
               soc=1149580800, frasec=16817)

# df.set_soc(1149580800)
# df.set_frasec(16817)

data_hex_result = str(binascii.hexlify(df.convert2bytes()), 'utf-8')

assert data_hex_string == data_hex_result, "Data Frame Error."


data_multi_hex_string = 'aa0100581e3644853600000041b10000392b0000e36ace7ce36a31830444000009c4000042c80000447a0000' \
                        '461c40003c120000392b0000e36ace7ce36a31830444000009c4000042c80000447a0000461c40003c12bd52'

dfm = DataFrame(7734, [('ok', True, 'timestamp', False, False, False, 0, '<10', 0),
                       ('ok', True, 'timestamp', False, False, False, 0, '<10', 0)],
                [[(14635, 0), (58218, 52860), (58218, 12675), (1092, 0)],
                [(14635, 0), (58218, 52860), (58218, 12675), (1092, 0)]], [2500, 2500], [0, 0],
                [[100, 1000, 10000], [100, 1000, 10000]], [[0x3c12], [0x3c12]], [0x0004, 0x0004], 2, 1149580800, 16817)

# dfm.set_soc(1149580800)
# dfm.set_frasec(16817)

data_multi_hex_result = str(binascii.hexlify(dfm.convert2bytes()), 'utf-8')

assert data_multi_hex_string == data_multi_hex_result, "Data Frame Multistreaming Error."

cfg_hex_string = 'aa3101c61e36448527f056071098000f4240000153746174696f6e2041202020202020201e360004000400030001564120' \
                 '20202020202020202020202020564220202020202020202020202020205643202020202020202020202020202049312020' \
                 '202020202020202020202020414e414c4f4731202020202020202020414e414c4f4732202020202020202020414e414c4f' \
                 '4733202020202020202020425245414b4552203120535441545553425245414b4552203220535441545553425245414b45' \
                 '52203320535441545553425245414b4552203420535441545553425245414b4552203520535441545553425245414b4552' \
                 '203620535441545553425245414b4552203720535441545553425245414b4552203820535441545553425245414b455220' \
                 '3920535441545553425245414b4552204120535441545553425245414b4552204220535441545553425245414b45522043' \
                 '20535441545553425245414b4552204420535441545553425245414b4552204520535441545553425245414b4552204620' \
                 '535441545553425245414b4552204720535441545553000df847000df847000df8470100b2d00000000101000001020000' \
                 '010000ffff00000016001ed5d1'

cfg = ConfigFrame2(7734, 1000000, 1, "Station A", 7734, (False, False, True, False), 4, 3, 1,
                   ["VA", "VB", "VC", "I1", "ANALOG1", "ANALOG2", "ANALOG3", "BREAKER 1 STATUS",
                    "BREAKER 2 STATUS", "BREAKER 3 STATUS", "BREAKER 4 STATUS", "BREAKER 5 STATUS",
                    "BREAKER 6 STATUS", "BREAKER 7 STATUS", "BREAKER 8 STATUS", "BREAKER 9 STATUS",
                    "BREAKER A STATUS", "BREAKER B STATUS", "BREAKER C STATUS", "BREAKER D STATUS",
                    "BREAKER E STATUS", "BREAKER F STATUS", "BREAKER G STATUS"],
                   [(915527, 'v'), (915527, 'v'), (915527, 'v'), (45776, 'i')],
                   [(1, 'pow'), (1, 'rms'), (1, 'peak')], [(0x0000, 0xffff)], 60, 22, 30,
                   1149577200, (463000, '-', False, True, 6))

# cfg.set_soc(1149577200)
# cfg.set_frasec(463000, '-', False, True, 6)

cfg_hex_result = str(binascii.hexlify(cfg.convert2bytes()), 'utf-8')

assert cfg_hex_result == cfg_hex_string, "Configuration Frame v2 Error."


cfg_multi_hex_string = 'aa3103741e36448527f056071098000f4240000253746174696f6e2041202020202020201e360004000400030001' \
                       '56412020202020202020202020202020564220202020202020202020202020205643202020202020202020202020' \
                       '202049312020202020202020202020202020414e414c4f4731202020202020202020414e414c4f47322020202020' \
                       '20202020414e414c4f4733202020202020202020425245414b4552203120535441545553425245414b4552203220' \
                       '535441545553425245414b4552203320535441545553425245414b4552203420535441545553425245414b455220' \
                       '3520535441545553425245414b4552203620535441545553425245414b4552203720535441545553425245414b45' \
                       '52203820535441545553425245414b4552203920535441545553425245414b455220412053544154555342524541' \
                       '4b4552204220535441545553425245414b4552204320535441545553425245414b45522044205354415455534252' \
                       '45414b4552204520535441545553425245414b4552204620535441545553425245414b4552204720535441545553' \
                       '000df847000df847000df8470100b2d00000000101000001020000010000ffff0000001653746174696f6e204120' \
                       '2020202020201e360004000400030001564120202020202020202020202020205642202020202020202020202020' \
                       '20205643202020202020202020202020202049312020202020202020202020202020414e414c4f47312020202020' \
                       '20202020414e414c4f4732202020202020202020414e414c4f4733202020202020202020425245414b4552203120' \
                       '535441545553425245414b4552203220535441545553425245414b4552203320535441545553425245414b455220' \
                       '3420535441545553425245414b4552203520535441545553425245414b4552203620535441545553425245414b45' \
                       '52203720535441545553425245414b4552203820535441545553425245414b455220392053544154555342524541' \
                       '4b4552204120535441545553425245414b4552204220535441545553425245414b45522043205354415455534252' \
                       '45414b4552204420535441545553425245414b4552204520535441545553425245414b4552204620535441545553' \
                       '425245414b4552204720535441545553000df847000df847000df8470100b2d00000000101000001020000010000' \
                       'ffff00000016001e20e8'

cfgm = ConfigFrame2(7734, 1000000, 2, ["Station A", "Station A"], [7734, 7734], [(False, False, True, False),
                                                                                 (False, False, True, False)],
                    [4, 4], [3, 3], [1, 1],
                    [["VA", "VB", "VC", "I1", "ANALOG1", "ANALOG2", "ANALOG3", "BREAKER 1 STATUS",
                      "BREAKER 2 STATUS", "BREAKER 3 STATUS", "BREAKER 4 STATUS", "BREAKER 5 STATUS",
                      "BREAKER 6 STATUS", "BREAKER 7 STATUS", "BREAKER 8 STATUS", "BREAKER 9 STATUS",
                      "BREAKER A STATUS", "BREAKER B STATUS", "BREAKER C STATUS", "BREAKER D STATUS",
                      "BREAKER E STATUS", "BREAKER F STATUS", "BREAKER G STATUS"],
                    ["VA", "VB", "VC", "I1", "ANALOG1", "ANALOG2", "ANALOG3", "BREAKER 1 STATUS",
                     "BREAKER 2 STATUS", "BREAKER 3 STATUS", "BREAKER 4 STATUS", "BREAKER 5 STATUS",
                     "BREAKER 6 STATUS", "BREAKER 7 STATUS", "BREAKER 8 STATUS", "BREAKER 9 STATUS",
                     "BREAKER A STATUS", "BREAKER B STATUS", "BREAKER C STATUS", "BREAKER D STATUS",
                     "BREAKER E STATUS", "BREAKER F STATUS", "BREAKER G STATUS"]],
                    [[(915527, 'v'), (915527, 'v'), (915527, 'v'), (45776, 'i')],
                     [(915527, 'v'), (915527, 'v'), (915527, 'v'), (45776, 'i')]],
                    [[(1, 'pow'), (1, 'rms'), (1, 'peak')], [(1, 'pow'), (1, 'rms'), (1, 'peak')]],
                    [[(0x0000, 0xffff)], [(0x0000, 0xffff)]], [60, 60], [22, 22], 30,
                    1149577200, (463000, '-', False, True, 6))

# cfgm.set_soc(1149577200)
# cfgm.set_frasec(463000, '-', False, True, 6)

cfg_multi_hex_result = str(binascii.hexlify(cfgm.convert2bytes()), 'utf-8')
assert cfg_multi_hex_result == cfg_multi_hex_string, "Configuration Frame v2 Multistreaming Error."

hf_hex_string = 'aa1100271e36448560300f0bbfd048656c6c6f2049276d20486561646572204672616d652e17cc'

hf = HeaderFrame(7734, "Hello I'm Header Frame.", 1149591600, (770000, '+', False, False, 15))
# hf.set_soc(1149591600)
# hf.set_frasec(770000, time_quality=15)

hf_hex_result = str(binascii.hexlify(hf.convert2bytes()), 'utf-8')

assert hf_hex_string == hf_hex_result, "Header Frame Error."

cf_hex_string = 'aa4100121e36448560300f0bbfd00002ce00'

cf = CommandFrame(7734, 'start', None, 1149591600, (770000, '+', False, False, 15))
# cf.set_soc(1149591600)
# cf.set_frasec(770000, time_quality=15)

cf_hex_result = str(binascii.hexlify(cf.convert2bytes()), 'utf-8')

assert cfg_hex_result == cfg_hex_string, "Command Frame Error."
