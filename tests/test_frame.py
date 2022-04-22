import unittest
import binascii
from synchrophasor.frame import ConfigFrame2
from synchrophasor.frame import DataFrame
from synchrophasor.frame import HeaderFrame
from synchrophasor.frame import CommandFrame

__author__ = "Stevan Sandi"
__copyright__ = "Copyright (c) 2016, Tomo Popovic, Stevan Sandi, Bozo Krstajic"
__credits__ = []
__license__ = "BSD-3"
__version__ = "1.0.0-alpha"


def _cfg1pmu():
    return ConfigFrame2(
        pmu_id_code=7734,
        time_base=1000000,
        num_pmu=1,
        station_name="Station A",
        id_code=7734,
        data_format=(False, False, True, False),
        phasor_num=4,
        analog_num=3,
        digital_num=1,
        channel_names=[
            "VA", "VB", "VC", "I1", "ANALOG1", "ANALOG2", "ANALOG3",
            "BREAKER 1 STATUS", "BREAKER 2 STATUS", "BREAKER 3 STATUS",
            "BREAKER 4 STATUS", "BREAKER 5 STATUS", "BREAKER 6 STATUS",
            "BREAKER 7 STATUS", "BREAKER 8 STATUS", "BREAKER 9 STATUS",
            "BREAKER A STATUS", "BREAKER B STATUS", "BREAKER C STATUS",
            "BREAKER D STATUS", "BREAKER E STATUS", "BREAKER F STATUS",
            "BREAKER G STATUS"
        ],
        ph_units=[
            (915527, "v"),
            (915527, "v"),
            (915527, "v"),
            (45776, "i"),
        ],
        an_units=[
            (1, "pow"),
            (1, "rms"),
            (1, "peak"),
        ],
        dig_units=[
            (0x0000, 0xffff),
        ],
        f_nom=60,
        cfg_count=22,
        data_rate=30,
        soc=1149577200,
        frasec=(463000, "-", False, True, 6))


def _cfg2pmus():
    return ConfigFrame2(
        pmu_id_code=7734,
        time_base=1000000,
        num_pmu=2,
        station_name=[
            "Station A",
            "Station A",
        ],
        id_code=[7734, 7734],
        data_format=[
            (False, False, True, False),
            (False, False, True, False),
        ],
        phasor_num=[4, 4],
        analog_num=[3, 3],
        digital_num=[1, 1],
        channel_names=[
            [
                "VA", "VB", "VC", "I1", "ANALOG1", "ANALOG2", "ANALOG3",
                "BREAKER 1 STATUS", "BREAKER 2 STATUS", "BREAKER 3 STATUS",
                "BREAKER 4 STATUS", "BREAKER 5 STATUS", "BREAKER 6 STATUS",
                "BREAKER 7 STATUS", "BREAKER 8 STATUS", "BREAKER 9 STATUS",
                "BREAKER A STATUS", "BREAKER B STATUS", "BREAKER C STATUS",
                "BREAKER D STATUS", "BREAKER E STATUS", "BREAKER F STATUS",
                "BREAKER G STATUS"
            ],
            [
                "VA", "VB", "VC", "I1", "ANALOG1", "ANALOG2", "ANALOG3",
                "BREAKER 1 STATUS", "BREAKER 2 STATUS", "BREAKER 3 STATUS",
                "BREAKER 4 STATUS", "BREAKER 5 STATUS", "BREAKER 6 STATUS",
                "BREAKER 7 STATUS", "BREAKER 8 STATUS", "BREAKER 9 STATUS",
                "BREAKER A STATUS", "BREAKER B STATUS", "BREAKER C STATUS",
                "BREAKER D STATUS", "BREAKER E STATUS", "BREAKER F STATUS",
                "BREAKER G STATUS"
            ]
        ],
        ph_units=[
            [(915527, "v"), (915527, "v"), (915527, "v"), (45776, "i")],
            [(915527, "v"), (915527, "v"), (915527, "v"), (45776, "i")],
        ],
        an_units=[
            [(1, "pow"), (1, "rms"), (1, "peak")],
            [(1, "pow"), (1, "rms"), (1, "peak")],
        ],
        dig_units=[
            [(0x0000, 0xffff)],
            [(0x0000, 0xffff)],
        ],
        f_nom=[60, 60],
        cfg_count=[22, 22],
        data_rate=30,
        soc=1149577200,
        frasec=(463000, "-", False, True, 6))


class TestConfigFrame2_convert2bytes(unittest.TestCase):

    def test_1_pmu(self):
        wnt = ""\
          "aa3101c61e36448527f056071098000f4240000153746174696f6e2041202020"\
          "202020201e360004000400030001564120202020202020202020202020205642"\
          "2020202020202020202020202020564320202020202020202020202020204931"\
          "2020202020202020202020202020414e414c4f4731202020202020202020414e"\
          "414c4f4732202020202020202020414e414c4f47332020202020202020204252"\
          "45414b4552203120535441545553425245414b45522032205354415455534252"\
          "45414b4552203320535441545553425245414b45522034205354415455534252"\
          "45414b4552203520535441545553425245414b45522036205354415455534252"\
          "45414b4552203720535441545553425245414b45522038205354415455534252"\
          "45414b4552203920535441545553425245414b45522041205354415455534252"\
          "45414b4552204220535441545553425245414b45522043205354415455534252"\
          "45414b4552204420535441545553425245414b45522045205354415455534252"\
          "45414b4552204620535441545553425245414b4552204720535441545553000d"\
          "f847000df847000df8470100b2d00000000101000001020000010000ffff0000"\
          "0016001ed5d1"

        self.assertEqual(_str(_cfg1pmu().convert2bytes()), wnt)

    def test_2_pmus(self):
        wnt = ""\
          "aa3103741e36448527f056071098000f4240000253746174696f6e2041202020"\
          "202020201e360004000400030001564120202020202020202020202020205642"\
          "2020202020202020202020202020564320202020202020202020202020204931"\
          "2020202020202020202020202020414e414c4f4731202020202020202020414e"\
          "414c4f4732202020202020202020414e414c4f47332020202020202020204252"\
          "45414b4552203120535441545553425245414b45522032205354415455534252"\
          "45414b4552203320535441545553425245414b45522034205354415455534252"\
          "45414b4552203520535441545553425245414b45522036205354415455534252"\
          "45414b4552203720535441545553425245414b45522038205354415455534252"\
          "45414b4552203920535441545553425245414b45522041205354415455534252"\
          "45414b4552204220535441545553425245414b45522043205354415455534252"\
          "45414b4552204420535441545553425245414b45522045205354415455534252"\
          "45414b4552204620535441545553425245414b4552204720535441545553000d"\
          "f847000df847000df8470100b2d00000000101000001020000010000ffff0000"\
          "001653746174696f6e2041202020202020201e36000400040003000156412020"\
          "2020202020202020202020205642202020202020202020202020202056432020"\
          "20202020202020202020202049312020202020202020202020202020414e414c"\
          "4f4731202020202020202020414e414c4f4732202020202020202020414e414c"\
          "4f4733202020202020202020425245414b455220312053544154555342524541"\
          "4b4552203220535441545553425245414b455220332053544154555342524541"\
          "4b4552203420535441545553425245414b455220352053544154555342524541"\
          "4b4552203620535441545553425245414b455220372053544154555342524541"\
          "4b4552203820535441545553425245414b455220392053544154555342524541"\
          "4b4552204120535441545553425245414b455220422053544154555342524541"\
          "4b4552204320535441545553425245414b455220442053544154555342524541"\
          "4b4552204520535441545553425245414b455220462053544154555342524541"\
          "4b4552204720535441545553000df847000df847000df8470100b2d000000001"\
          "01000001020000010000ffff00000016001e20e8"

        self.assertEqual(_str(_cfg2pmus().convert2bytes()), wnt)


class TestDataFrame_convert2bytes(unittest.TestCase):

    def test_1_pmu(self):
        frm = DataFrame(
            pmu_id_code=7734,
            stat=("ok", True, "timestamp", False, False, False, 0, "<10", 0),
            phasors=[(14635, 0), (-7318, -12676), (-7318, 12675), (1092, 0)],
            freq=2500,
            dfreq=0,
            analog=[100, 1000, 10000],
            digital=[0x3c12],
            cfg=_cfg1pmu(),
            soc=1149580800,
            frasec=16817,
        )

        wnt = ""\
            "aa0100341e3644853600000041b10000392b0000e36ace7ce36a318304440000"\
            "09c4000042c80000447a0000461c40003c12d43f"

        self.assertEqual(_str(frm.convert2bytes()), wnt)

    def test_2_pmus(self):
        frm = DataFrame(
            pmu_id_code=7734,
            stat=[("ok", True, "timestamp", False, False, False, 0, "<10", 0),
                  ("ok", True, "timestamp", False, False, False, 0, "<10", 0)],
            phasors=[
                [(14635, 0), (-7318, -12676), (-7318, 12675), (1092, 0)],
                [(14635, 0), (-7318, -12676), (-7318, 12675), (1092, 0)],
            ],
            freq=[2500, 2500],
            dfreq=[0, 0],
            analog=[[100, 1000, 10000], [100, 1000, 10000]],
            digital=[[0x3c12], [0x3c12]],
            cfg=_cfg2pmus(),
            soc=1149580800,
            frasec=16817,
        )

        wnt = ""\
            "aa0100581e3644853600000041b10000392b0000e36ace7ce36a318304440000"\
            "09c4000042c80000447a0000461c40003c120000392b0000e36ace7ce36a3183"\
            "0444000009c4000042c80000447a0000461c40003c12bd52"

        self.assertEqual(_str(frm.convert2bytes()), wnt)


class TestHeaderFrame_convert2bytes(unittest.TestCase):

    def test_ok(self):
        frm = HeaderFrame(
            pmu_id_code=7734,
            header="Hello I'm Header Frame.",
            soc=1149591600,
            frasec=(770000, "+", False, False, 15),
        )

        wnt = ""\
            "aa1100271e36448560300f0bbfd048656c6c6f2049276d204865616465722046"\
            "72616d652e17cc"

        self.assertEqual(_str(frm.convert2bytes()), wnt)


class TestCommandFrame_convert2bytes(unittest.TestCase):

    def test_ok(self):
        frm = CommandFrame(
            pmu_id_code=7734,
            command="start",
            extended_frame=None,
            soc=1149591600,
            frasec=(770000, "+", False, False, 15),
        )

        wnt = "aa4100121e36448560300f0bbfd00002ce00"

        self.assertEqual(_str(frm.convert2bytes()), wnt)


def _str(bs):
    return str(binascii.hexlify(bs), "utf-8")
