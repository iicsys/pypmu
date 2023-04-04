"""
# IEEE Std C37.118.2 - 2011 Frame Implementation #

This script provides implementation  of IEEE Standard for Synchrophasor
Data Transfer for Power Systems.

**IEEE C37.118.2 standard** defines four types of frames:

* Data Frames.
* Configuration Frames (multiple versions).
* Command Frames.
* Header Frames.

"""

import collections.abc as collections
from abc import ABCMeta, abstractmethod
from struct import pack, unpack
from time import time
from math import sqrt, atan2

from synchrophasor.utils import crc16xmodem
from synchrophasor.utils import list2bytes


__author__ = "Stevan Sandi"
__copyright__ = "Copyright (c) 2016, Tomo Popovic, Stevan Sandi, Bozo Krstajic"
__credits__ = []
__license__ = "BSD-3"
__version__ = "1.0.0-alpha"


class CommonFrame(metaclass=ABCMeta):
    """
    ## CommonFrame ##

    CommonFrame is abstract class which represents words (fields) common to all frame types.

    Class contains two abstract methods:

    * ``convert2bytes()`` - for converting frame to bytes convenient for sending.
    * ``convert2frame()`` - which converts array of bytes to specific frame.

    Both of these methods must must be implemented for each frame type.

    Following attributes are common for all frame types:

    **Attributes:**

    * ``frame_type`` **(int)** - Defines frame type.
    * ``version`` **(int)** - Standard version. Default value: ``1``.
    * ``pmu_id_code`` **(int)** - Data stream ID number.
    * ``soc`` **(int)** - UNIX timestamp. Default value: ``None``.
    * ``frasec`` **(int)** - Fraction of second and Time Quality. Default value: ``None``.

    **Raises:**

        FrameError
    When it's not possible to create valid frame, usually due invalid parameter value.
    """

    FRAME_TYPES = {"data": 0, "header": 1, "cfg1": 2, "cfg2": 3, "cfg3": 5, "cmd": 4}

    # Invert FRAME_TYPES codes to get FRAME_TYPE_WORDS
    FRAME_TYPES_WORDS = {code: word for word, code in FRAME_TYPES.items()}

    def __init__(self, frame_type, pmu_id_code, soc=None, frasec=None, version=1):
        """
        CommonFrame abstract class
        :param string frame_type: Defines frame type
        :param int pmu_id_code: Standard version. Default value: ``1``
        :param int soc:
        :param int frasec:
        :param int version:
        :return:
        """

        self.set_frame_type(frame_type)
        self.set_version(version)
        self.set_id_code(pmu_id_code)

        if soc or frasec:
            self.set_time(soc, frasec)

    def set_frame_type(self, frame_type):
        """
        ### set_frame_type() ###

        Setter for ``frame_type``.

        **Params:**

        * ``frame_type`` **(int)** - Should be one of 6 possible values from FRAME_TYPES dict.
        Frame types with integer and binary representations are shown below.
        ______________________________________________________________________________________

            +--------------+----------+-----------+
            |  Frame type  |  Decimal |   Binary  |
            +--------------+----------+-----------+
            | Data         |     0    |    000    |
            +--------------+----------+-----------+
            | Header       |     1    |    001    |
            +--------------+----------+-----------+
            | Config v1    |     2    |    010    |
            +--------------+----------+-----------+
            | Config v2    |     3    |    011    |
            +--------------+----------+-----------+
            | Command      |     4    |    100    |
            +--------------+----------+-----------+
            | Config v3    |     5    |    101    |
            +--------------+----------+-----------+


        **Raises:**

            FrameError
        When ``frame type`` value provided is not specified in ``FRAME_TYPES``.

        """

        if frame_type not in CommonFrame.FRAME_TYPES:
            raise FrameError("Unknown frame type. Possible options: [data, header, cfg1, cfg2, cfg3, cmd].")
        else:
            self._frame_type = CommonFrame.FRAME_TYPES[frame_type]

    def get_frame_type(self):

        return CommonFrame.FRAME_TYPES_WORDS[self._frame_type]

    def extract_frame_type(byte_data):
        """This method will only return type of the frame. It shall be used for stream splitter
        since there is no need to create instance of specific frame which will cause lower performance."""

        # Check if frame is valid
        if not CommandFrame._check_crc(byte_data):
            raise FrameError("CRC failed. Frame not valid.")

        # Get second byte and determine frame type by shifting right to get higher 4 bits
        frame_type = int.from_bytes([byte_data[1]], byteorder="big", signed=False) >> 4

        return CommonFrame.FRAME_TYPES_WORDS[frame_type]

    def set_version(self, version):
        """
        ### set_version() ###

        Setter for frame IEEE standard ``version``.

        **Params:**

        * ``version`` **(int)** - Should be number between ``1`` and ``15``.

        **Raises:**

            FrameError
        When ``version`` value provided is out of range.

        """

        if not 1 <= version <= 15:
            raise FrameError("VERSION number out of range. 1<= VERSION <= 15")
        else:
            self._version = version

    def get_version(self):

        return self._version

    def set_id_code(self, id_code):
        """
        ### set_id_code() ###

        Setter for ``pmu_id_code`` as data stream identified.

        **Params:**

        * ``id_code`` **(int)** - Should be number between ``1`` and ``65534``.

        **Raises:**

            FrameError
        When ``id_code`` value provided is out of range.

        """

        if not 1 <= id_code <= 65534:
            raise FrameError("ID CODE out of range. 1 <= ID_CODE <= 65534")
        else:
            self._pmu_id_code = id_code

    def get_id_code(self):

        return self._pmu_id_code

    def set_time(self, soc=None, frasec=None):
        """
        ### set_time() ###

        Setter for ``soc`` and ``frasec``. If values for ``soc`` or ``frasec`` are
        not provided this method will calculate them.

        **Params:**

        * ``soc`` **(int)** - UNIX timestamp, 32-bit unsigned number. See ``set_soc()``
        method.
        * ``frasec`` **(int)** or **(tuple)** - Fracion of second and Time Quality. See
        ``set_frasec`` method.

        **Raises:**

            FrameError
        When ``soc`` value provided is out of range.

        When ``frasec`` is not valid.

        """

        t = time()  # Get current timestamp

        if soc:
            self.set_soc(soc)
        else:
            self.set_soc(int(t))  # Get current timestamp

        if frasec:
            if isinstance(frasec, collections.Sequence):
                self.set_frasec(*frasec)
            else:
                self.set_frasec(frasec)  # Just set fraction of second and use default values for other arguments.
        else:
            # Calculate fraction of second (after decimal point) using only first 7 digits to avoid
            # overflow (24 bit number).
            self.set_frasec(int((((repr((t % 1))).split("."))[1])[0:6]))

    def set_soc(self, soc):
        """
        ### set_soc() ###

        Setter for ``soc`` as second of century.

        **Params:**

        * ``soc`` **(int)** - UNIX timestamp, should be between ``0`` and ``4294967295``.

        **Raises:**

            FrameError
        When ``soc`` value provided is out of range.

        """

        if not 0 <= soc <= 4294967295:
            raise FrameError("Time stamp out of range. 0 <= SOC <= 4294967295")
        else:
            self._soc = soc

    def get_soc(self):

        return self._soc

    def set_frasec(self, fr_seconds, leap_dir="+", leap_occ=False, leap_pen=False, time_quality=0):
        """
        ### set_frasec() ###

        Setter for ``frasec`` as Fraction of Second and Time Quality.

        **Params:**

        *    ``fr_seconds`` **(int)** - Fraction of Second as 24-bit unsigned number.
             Should be between ``0`` and ``16777215``.
        *    ``leap_dir`` **(char)** - Leap Second Direction: ``+`` for add (``0``), ``-`` for
             delete (``1``).
             Default value: ``+``.
        *    ``leap_occ`` **(bool)** - Leap Second Occurred: ``True`` in the first second after
             the leap second occurs and remains set for 24h.
        *    ``leap_pen`` **(bool)** - Leap Second Pending: ``True`` not more than 60 s nor less
             than 1 s before a leap second occurs, and cleared in the second after the leap
             second occurs.
        *    ``time_quality`` **(int)** - Message Time Quality represents worst-case clock
             accuracy according to UTC. Table below shows code values. Should be between ``0``
             and ``15``.
        __________________________________________________________________________________________
            +------------+----------+---------------------------+
            |  Binary    |  Decimal |           Value           |
            +------------+----------+---------------------------+
            | 1111       |    15    | Fault - clock failure.    |
            +------------+----------+---------------------------+
            | 1011       |    11    | Time within 10s of UTC.   |
            +------------+----------+---------------------------+
            | 1010       |    10    | Time within 1s of UTC.    |
            +------------+----------+---------------------------+
            | 1001       |    9     | Time within 10^-1s of UTC.|
            +------------+----------+---------------------------+
            | 1000       |    8     | Time within 10^-2s of UTC.|
            +------------+----------+---------------------------+
            | 0111       |    7     | Time within 10^-3s of UTC.|
            +------------+----------+---------------------------+
            | 0110       |    6     | Time within 10^-4s of UTC.|
            +------------+----------+---------------------------+
            | 0101       |    5     | Time within 10^-5s of UTC.|
            +------------+----------+---------------------------+
            | 0100       |    4     | Time within 10^-6s of UTC.|
            +------------+----------+---------------------------+
            | 0011       |    3     | Time within 10^-7s of UTC.|
            +------------+----------+---------------------------+
            | 0010       |    2     | Time within 10^-8s of UTC.|
            +------------+----------+---------------------------+
            | 0001       |    1     | Time within 10^-9s of UTC.|
            +------------+----------+---------------------------+
            | 0000       |    0     | Clock locked to UTC.      |
            +------------+----------+---------------------------+



        **Raises:**

            FrameError
        When ``fr_seconds`` value provided is out of range.

        When ``time_quality`` value provided is out of range.

        """

        if not 0 <= fr_seconds <= 16777215:
            raise FrameError("Frasec out of range. 0 <= FRASEC <= 16777215 ")

        if (not 0 <= time_quality <= 15) or (time_quality in [12, 13, 14]):
            raise FrameError("Time quality flag out of range. 0 <= MSG_TQ <= 15")

        if leap_dir not in ["+", "-"]:
            raise FrameError("Leap second direction must be '+' or '-'")

        frasec = 1 << 1  # Bit 7: Reserved for future use. Not important but it will be 1 for easier byte forming.

        if leap_dir == "-":  # Bit 6: Leap second direction [+ = 0] and [- = 1].
            frasec |= 1

        frasec <<= 1

        if leap_occ:  # Bit 5: Leap Second Occurred, 1 in first second after leap second, remains 24h.
            frasec |= 1

        frasec <<= 1

        if leap_pen:  # Bit 4: Leap Second Pending - shall be 1 not more then 60s nor less than 1s before leap second.
            frasec |= 1

        frasec <<= 4  # Shift left 4 bits for message time quality

        # Bit 3 - 0: Message Time Quality indicator code - integer representation of bits (check table).
        frasec |= time_quality

        mask = 1 << 7  # Change MSB to 0 for standard compliance.
        frasec ^= mask

        frasec <<= 24  # Shift 24 bits for fractional time.

        frasec |= fr_seconds  # Bits 23-0: Fraction of second.

        self._frasec = frasec

    def get_frasec(self):

        return self._int2frasec(self._frasec)

    @staticmethod
    def _int2frasec(frasec_int):

        tq = frasec_int >> 24
        leap_dir = tq & 0b01000000
        leap_occ = tq & 0b00100000
        leap_pen = tq & 0b00010000

        time_quality = tq & 0b00001111

        # Reassign values to create Command frame
        leap_dir = "-" if leap_dir else "+"
        leap_occ = bool(leap_occ)
        leap_pen = bool(leap_pen)

        fr_seconds = frasec_int & (2**23 - 1)

        return fr_seconds, leap_dir, leap_occ, leap_pen, time_quality

    @staticmethod
    def _get_data_format_size(data_format):
        """
        ### get_data_format() ###

        Getter for frame data format.

        **Params:**

        * ``data_format`` **(bytes)** - Data format in data frames. Should be 16-bit flag.

        **Returns:**

        * ``dict`` with PHASOR, ANALOG, and FREQ measurement size in bytes.
        ``{'phasor' : phasors_byte_size, 'analog' : analog_byte_size, 'freq' : freq_byte_size}``

        """

        if (data_format & 2) != 0:  # If second bit in data_format is 0 16x2 bits = 4 bytes otherwise 8 (2xfloat).
            phasors_byte_size = 8
        else:
            phasors_byte_size = 4

        if (data_format & 4) != 0:  # If third bit in data_format is 0 16 bits = 2 bytes otherwise 4 bytes (float).
            analog_byte_size = 4
        else:
            analog_byte_size = 2

        if (data_format & 8) != 0:  # If fourth bit in data_format is 0 16 bits = 2 bytes otherwise 4 bytes (float).
            freq_byte_size = 4
        else:
            freq_byte_size = 2

        return {"phasor": phasors_byte_size, "analog": analog_byte_size, "freq": freq_byte_size}

    def set_data_format(self, data_format, num_streams):
        """
        ### set_data_format() ###

        Setter for frame data format. If number of data streams sent by PMUs is larger then
        ``1`` data format should be provided for each data stream. Data format might be
        represented as integer number as shown in table below where ordered letters represent
        ``(PHASOR_RECT/POLAR; PHASOR_INT/FLOAT; ANALOG_INT/FLOAT; FREQ_INT/FLOAT)`` format, where
        ``R`` means RECTANGULAR, ``P`` means POLAR, ``I`` means 16 bit INTEGER and ``F`` means FLOAT.
        Beside this, data format might be provided as tuple of bool values ordered as mentioned
        before.
        __________________________________________________________________________________________

            +--------------+----------+
            |  Data Format |  Decimal |
            +--------------+----------+
            | (R;I;I;I)    |     0    |
            +--------------+----------+
            | (P;I;I;I)    |     1    |
            +--------------+----------+
            | (R;F;I;I)    |     2    |
            +--------------+----------+
            | (P;F;I;I)    |     3    |
            +--------------+----------+
            | (R;I;F;I)    |     4    |
            +--------------+----------+
            | (P;I;F;I)    |     5    |
            +--------------+----------+
            | (R;F;F;I)    |     6    |
            +--------------+----------+
            | (P;F;F;I)    |     7    |
            +--------------+----------+
            | (R;I;I;F)    |     8    |
            +--------------+----------+
            | (P;I;I;F)    |     9    |
            +--------------+----------+
            | (R;F;I;F)    |    10    |
            +--------------+----------+
            | (P;F;I;F)    |    11    |
            +--------------+----------+
            | (R;I;F;F)    |    12    |
            +--------------+----------+
            | (P;I;F;F)    |    13    |
            +--------------+----------+
            | (R;F;F;F)    |    14    |
            +--------------+----------+
            | (P;F;F;F)    |    15    |
            +--------------+----------+

        **Params:**

        * ``data_format`` **(mixed)** - If number of data streams is larger then ``1`` should be list
        of tuples or integers, otherwise single ``tuple`` or ``int`` expected.
        * ``num_streams`` **(int)** - Number of data measurement streams packed in one data frame.

        **Raises:**

            FrameError
        When length of ``data_format`` list is not equal to ``num_stream`` and ``num_stream`` is
        larger then ``1``.

        When ``data_format`` value provided is out of range.

        """

        if num_streams > 1:
            if not isinstance(data_format, list) or num_streams != len(data_format):
                raise FrameError("When NUM_STREAMS > 1 provide FORMATs as list with NUM_STREAMS elements.")

            data_formats = []  # Format tuples transformed to ints
            for format_type in data_format:
                if isinstance(format_type, tuple):  # If data formats are specified as tuples then convert them to ints
                    data_formats.append(CommonFrame._format2int(*format_type))
                else:
                    if not 0 <= format_type <= 15:  # If data formats are specified as ints check range
                        raise FrameError("Format Type out of range. 0 <= FORMAT <= 15")
                    else:
                        data_formats.append(format_type)

                self._data_format = data_formats
        else:
            if isinstance(data_format, tuple):
                self._data_format = CommonFrame._format2int(*data_format)
            else:
                if not 0 <= data_format <= 15:
                    raise FrameError("Format Type out of range. 0 <= FORMAT <= 15")
                self._data_format = data_format

    def get_data_format(self):

        if isinstance(self._data_format, list):
            return [self._int2format(df) for df in self._data_format]
        else:
            return self._int2format(self._data_format)

    @staticmethod
    def _format2int(phasor_polar=False, phasor_float=False, analogs_float=False, freq_float=False):
        """
        ### format2int() ###

        Convert ``boolean`` representation of data format to integer.

        **Params:**

        * ``phasor_polar`` **(bool)** - If ``True`` phasor represented using magnitude and angle (polar)
        else rectangular.
        * ``phasor_float`` **(bool)** - If ``True`` phasor represented using floating point format else
        represented as 16 bit integer.
        * ``analogs_float`` **(bool)** - If ``True`` analog values represented using floating point notation
        else represented as 16 bit integer.
        * ``freq_float`` **(bool)** - If ``True`` FREQ/DFREQ represented using floating point notation
        else represented as 16 bit integer.

        **Returns:**

        * ``int`` representation of data format.

        """

        data_format = 1 << 1

        if freq_float:
            data_format |= 1
        data_format <<= 1

        if analogs_float:
            data_format |= 1
        data_format <<= 1

        if phasor_float:
            data_format |= 1
        data_format <<= 1

        if phasor_polar:
            data_format |= 1

        mask = 1 << 4
        data_format ^= mask

        return data_format

    @staticmethod
    def _int2format(data_format):

        phasor_polar = data_format & 0b0001
        phasor_float = data_format & 0b0010
        analogs_float = data_format & 0b0100
        freq_float = data_format & 0b1000

        return bool(phasor_polar), bool(phasor_float), bool(analogs_float), bool(freq_float)

    @staticmethod
    def _check_crc(byte_data):

        crc_calculated = crc16xmodem(byte_data[0:-2], 0xffff).to_bytes(2, "big")  # Calculate CRC

        if byte_data[-2:] != crc_calculated:
            return False

        return True

    @abstractmethod
    def convert2bytes(self, byte_message):

        # SYNC word in CommonFrame starting with AA hex word + frame type + version
        sync_b = (0xaa << 8) | (self._frame_type << 4) | self._version
        sync_b = sync_b.to_bytes(2, "big")

        # FRAMESIZE: 2B SYNC + 2B FRAMESIZE + 2B IDCODE + 4B SOC + 4B FRASEC + len(Command) + 2B CHK
        frame_size_b = (16 + len(byte_message)).to_bytes(2, "big")

        # PMU ID CODE
        pmu_id_code_b = self._pmu_id_code.to_bytes(2, "big")

        # If timestamp not given set timestamp
        if not hasattr(self, "_soc") and not hasattr(self, "_frasec"):
            self.set_time()
        elif not self._soc and not self._frasec:
            self.set_time()

        # SOC
        soc_b = self._soc.to_bytes(4, "big")

        # FRASEC
        frasec_b = self._frasec.to_bytes(4, "big")

        # CHK
        crc_chk_b = crc16xmodem(sync_b + frame_size_b + pmu_id_code_b + soc_b + frasec_b + byte_message, 0xffff)

        return sync_b + frame_size_b + pmu_id_code_b + soc_b + frasec_b + byte_message + crc_chk_b.to_bytes(2, "big")

    @abstractmethod
    def convert2frame(byte_data, cfg=None):

        convert_method = {
            0: DataFrame.convert2frame,
            1: HeaderFrame.convert2frame,
            2: ConfigFrame1.convert2frame,
            3: ConfigFrame2.convert2frame,
            4: CommandFrame.convert2frame,
            5: ConfigFrame3.convert2frame,
        }

        if not CommonFrame._check_crc(byte_data):
            raise FrameError("CRC failed. Frame not valid.")

        # Get second byte and determine frame type by shifting right to get higher 4 bits
        frame_type = int.from_bytes([byte_data[1]], byteorder="big", signed=False) >> 4

        if frame_type == 0:  # DataFrame pass Configuration to decode message
            return convert_method[frame_type](byte_data, cfg)

        return convert_method[frame_type](byte_data)


class ConfigFrame1(CommonFrame):
    """
    ## ConfigFrame1 ##

    ConfigFrame1 is class which represents configuration frame v1.
    Configuration frame version 1 carries info about device reporting
    ability.

    Class implements two abstract methods from super class.

    * ``convert2bytes()`` - for converting ConfigFrame1 to bytes.
    * ``convert2frame()`` - which converts array of bytes to ConfigFrame1.

    Each instance of ConfigFrame1 class will have following attributes.

    **Attributes:**

    * ``frame_type`` **(int)** - Defines frame type. Inherited from ``CommonFrame``.
    * ``version`` **(int)** - Standard version. Inherited from ``CommonFrame``. Default value: ``1``.
    * ``pmu_id_code`` **(int)** - PMU Id code which identifies data stream. Inherited from ``CommonFrame``.
    * ``soc`` **(int)** - UNIX timestamp. Default value: ``None``. Inherited from ``CommonFrame``.
    * ``frasec`` **(int)** - Fraction of second and Time Quality. Default value: ``None``.
      Inherited from ``CommonFrame``.
    * ``time_base`` **(int)** - Resolution of the fractional second time stamp in all frames.
    * ``num_pmu`` **(int)** - Number of PMUs (data streams) included in single ``DataFrame``.
    * ``multistreaming`` **(bool)** - ``True`` if ``num_pmu > 1``. That means data frame consist of multiple
      measurement streams.
    * ``station_name`` **(mixed)** - Station name ``(string)`` or station names ``(list)`` if ``multistreaming``.
    * ``id_code`` **(mixed)** - Measurement stream ID code ``(int)`` or ``(list)`` if ``multistreaming``. Each ID
      identifies source PMU of each data block.
    * ``data_format`` **(mixed)** - Data format for each data stream. Inherited from ``CommonFrame``.
    * ``phasor_num`` **(mixed)** - Number of phasors ``(int)`` or ``(list)`` if ``multistreaming``.
    * ``analog_num`` **(mixed)** - Number of analog values ``(int)`` or ``(list)`` if ``multistreaming``.
    * ``digital_num`` **(mixed)** - Number of digital status words ``(int)`` or ``(list)`` if ``multistreaming``.
    * ``channel_names`` **(list)** - List of phasor and channel names for phasor, analog and digital channel.
      If ``multistreaming`` it's list of lists.
    * ``ph_units`` **(list)** - Conversion factor for phasor channels. If ``multistreaming`` list of lists.
    * ``an_units`` **(list)** - Conversion factor for analog channels. If ``multistreaming`` list of lists.
    * ``dig_units`` **(list)** - Mask words for digital status word. If ``multistreaming`` list of lists.
    * ``fnom``  **(mixed)** - Nominal frequency code and flags. If ``multistreaming`` list of ints.
    * ``cfg_count`` **(mixed)** - Configuration change count. If ``multistreaming`` list of ints.
    * ``data_rate`` **(int)** - Frames per second or seconds per frame (if negative ``int``).

    **Raises:**

        FrameError
    When it's not possible to create valid frame, usually due invalid parameter value.
    """

    def __init__(self, pmu_id_code, time_base, num_pmu, station_name, id_code, data_format, phasor_num, analog_num,
                 digital_num, channel_names, ph_units, an_units, dig_units, f_nom, cfg_count, data_rate,
                 soc=None, frasec=None, version=1):

        super().__init__("cfg1", pmu_id_code, soc, frasec, version)  # Init CommonFrame with 'cfg1' frame type

        self.set_time_base(time_base)
        self.set_num_pmu(num_pmu)
        self.set_stn_names(station_name)
        self.set_stream_id_code(id_code)
        self.set_data_format(data_format, num_pmu)
        self.set_phasor_num(phasor_num)
        self.set_analog_num(analog_num)
        self.set_digital_num(digital_num)
        self.set_channel_names(channel_names)
        self.set_phasor_units(ph_units)
        self.set_analog_units(an_units)
        self.set_digital_units(dig_units)
        self.set_fnom(f_nom)
        self.set_cfg_count(cfg_count)
        self.set_data_rate(data_rate)

    def set_time_base(self, time_base):
        """
        ### set_time_base() ###

        Setter for time base. Resolution of the fractional second time stamp (FRASEC).
        Bits 31-24: Reserved for flags (high 8 bits).
        Bits 23-0: 24-bit unsigned integer which subdivision of the second that the FRASEC
        is based on.

        **Params:**

        * ``time_base`` **(int)** - Should be number between ``1`` and ``16777215``.

        **Raises:**

            FrameError
        When ``time_base`` value provided is out of range.

        """

        if not 1 <= time_base <= 16777215:
            raise FrameError("Time Base out of range. 1 <= TIME_BASE <= 16777215 ")
        else:
            self._time_base = time_base

    def get_time_base(self):

        return self._time_base

    def set_num_pmu(self, num_pmu):
        """
        ### set_num_pmu() ###

        Setter for number of PMUs. The number of PMUs included in data frame. No limit
        specified. The actual limit will be determined by the limit of 65 535 bytes in one
        frame (FRAMESIZE filed).

        Also, if ``num_pmu`` > ``1`` multistreaming will be set to ``True`` meaning that
        more then one data stream will be sent inside data frame.

        **Params:**

        * ``num_pmu`` **(int)** - Should be number between ``1`` and ``65535``.

        **Raises:**

            FrameError
        When ``num_pmu`` value provided is out of range.

        """

        if not 1 <= num_pmu <= 65535:
            raise FrameError("Number of PMUs out of range. 1 <= NUM_PMU <= 65535")
        else:
            self._num_pmu = num_pmu
            self._multistreaming = True if num_pmu > 1 else False

    def get_num_pmu(self):

        return self._num_pmu

    def is_multistreaming(self):

        return self._multistreaming

    def set_stn_names(self, station_name):
        """
        ### set_stn_names() ###

        Setter for station names.

        If ``multistreaming`` should be list of ``num_pmu`` station names otherwise 16
        character ASCII string.

        **Params:**

        * ``station_name`` **(mixed)** - Should be 16 bytes (16 ASCII characters) string
        or list of strings.

        **Raises:**

            FrameError
        When ``station_name`` is not list with length ``num_pmu`` when ``multistreaming``.

        """

        if self._multistreaming:
            if not isinstance(station_name, list) or self._num_pmu != len(station_name):
                raise FrameError("When NUM_PMU > 1 provide station names as list with NUM_PMU elements.")

            self._station_name = [station[:16].ljust(16, " ") for station in station_name]
        else:
            self._station_name = station_name[:16].ljust(16, " ")

    def get_station_name(self):

        return self._station_name

    def set_stream_id_code(self, id_code):
        """
        ### set_config_id_code() ###

        Setter for data stream IDs inside data frame.

        If ``multistreaming`` should be
        a list of IDs otherwise should be same as ``pmu_id_code``.

        **Params:**

        * ``id_code`` **(mixed)** - Should be number between ``1`` and ``65534``.
        If ``multistreaming`` list of numbers.

        **Raises:**

            FrameError
        When ``id_code`` is not list with length ``num_pmu`` when ``multistreaming``.
        When ``id_code`` value is out of range.

        """

        if self._multistreaming:
            if not isinstance(id_code, list) or self._num_pmu != len(id_code):
                raise FrameError("When NUM_PMU > 1 provide PMU ID codes as list with NUM_PMU elements.")

            for stream_id in id_code:
                if not 1 <= stream_id <= 65534:
                    raise FrameError("ID CODE out of range. 1 <= ID_CODE <= 65534")
        else:
            if not 1 <= id_code <= 65534:
                raise FrameError("ID CODE out of range. 1 <= ID_CODE <= 65534")

        self._id_code = id_code

    def get_stream_id_code(self):

        return self._id_code

    def set_phasor_num(self, phasor_num):
        """
        ### set_phasor_num() ###

        Setter for number of phasor measurements. Should be specified for each
        data stream in data frame.

        If ``multistreaming`` should be a list of ``integers`` otherwise should be ``integer``.

        **Params:**

        * ``phasor_num`` **(mixed)** - Should be integer between ``1`` and ``65535``.
        If ``multistreaming`` list of numbers.

        **Raises:**

            FrameError
        When ``phasor_num`` is not list with length ``num_pmu`` when ``multistreaming``.
        When ``phasor_num`` value is out of range.

        """

        if self._multistreaming:
            if not isinstance(phasor_num, list) or self._num_pmu != len(phasor_num):
                raise FrameError("When NUM_PMU > 1 provide PHNMR as list with NUM_PMU elements.")

            for phnmr in phasor_num:
                if not 0 <= phnmr <= 65535:
                    raise FrameError("Number of phasors out of range. 0 <= PHNMR <= 65535")
        else:
            if not 0 <= phasor_num <= 65535:
                raise FrameError("Number of phasors out of range. 0 <= PHNMR <= 65535")

        self._phasor_num = phasor_num

    def get_phasor_num(self):

        return self._phasor_num

    def set_analog_num(self, analog_num):
        """
        ### set_analog_num() ###

        Setter for number analog values. Should be specified for each
        data stream in data frame.

        If ``multistreaming`` should be a list of ``integers`` otherwise should be ``integer``.

        **Params:**

        * ``analog_num`` **(mixed)** - Should be integer between ``1`` and ``65535``.
        If ``multistreaming`` list of numbers.

        **Raises:**

            FrameError
        When ``analog_num`` is not list with length ``num_pmu`` when ``multistreaming``.
        When ``analog_num`` value is out of range.

        """

        if self._multistreaming:
            if not isinstance(analog_num, list) or self._num_pmu != len(analog_num):
                raise FrameError("When NUM_PMU > 1 provide ANNMR as list with NUM_PMU elements.")

            for annmr in analog_num:
                if not 0 <= annmr <= 65535:
                    raise FrameError("Number of phasors out of range. 0 <= ANNMR <= 65535")
        else:
            if not 0 <= analog_num <= 65535:
                raise FrameError("Number of phasors out of range. 0 <= ANNMR <= 65535")

        self._analog_num = analog_num

    def get_analog_num(self):

        return self._analog_num

    def set_digital_num(self, digital_num):
        """
        ### set_digital_num() ###

        Setter for number of digital status words. Should be specified for each
        data stream in data frame.

        If ``multistreaming`` should be a list of ``integers`` otherwise should be ``integer``.

        **Params:**

        * ``digital_num`` **(mixed)** - Should be integer between ``1`` and ``65535``.
        If ``multistreaming`` list of numbers.

        **Raises:**

            FrameError
        When ``digital_num`` is not list with length ``num_pmu`` when ``multistreaming``.
        When ``digital_num`` value is out of range.

        """
        if self._multistreaming:
            if not isinstance(digital_num, list) or self._num_pmu != len(digital_num):
                raise FrameError("When NUM_PMU > 1 provide DGNMR as list with NUM_PMU elements.")

            for dgnmr in digital_num:
                if not 0 <= dgnmr <= 65535:
                    raise FrameError("Number of phasors out of range. 0 <= DGNMR <= 65535")
        else:
            if not 0 <= digital_num <= 65535:
                raise FrameError("Number of phasors out of range. 0 <= DGNMR <= 65535")

        self._digital_num = digital_num

    def get_digital_num(self):

        return self._digital_num

    def set_channel_names(self, channel_names):
        """
        ### set_channel_names() ###

        Setter for phasor and channel names.

        **Params:**

        * ``channel_names`` **(list)** - Should be list of strings (16 ASCII character) with
        ``PHASOR_NUM`` + ``ANALOG_NUM`` + 16 * ``DIGITAL_NUM`` elements.
        If ``multistreaming`` should be list of lists.

        **Raises:**

            FrameError
        When ``channel_names`` is not list of lists with length ``num_pmu`` when ``multistreaming``.
        When ``channel_names`` is not list with ``PHASOR_NUM`` + ``ANALOG_NUM`` +
        + 16 * ``DIGITAL_NUM`` elements.

        """

        if self._multistreaming:
            if not all(isinstance(el, list) for el in channel_names) or self._num_pmu != len(channel_names):
                raise FrameError("When NUM_PMU > 1 provide CHNAM as list of lists with NUM_PMU elements.")

            channel_name_list = []
            for i, chnam in enumerate(channel_names):
                # Channel names must be list with PHNMR + ANNMR + 16*DGNMR elements. Each bit in one digital word
                # (16bit) has it's own label.
                if (self._phasor_num[i] + self._analog_num[i] + 16 * self._digital_num[i]) != len(chnam):
                    raise FrameError("Provide CHNAM as list with PHNMR + ANNMR + 16*DGNMR elements for each stream.")
                channel_name_list.append([chn[:16].ljust(16, " ") for chn in chnam])

            self._channel_names = channel_name_list
        else:
            if not isinstance(channel_names, list) or \
                    (self._phasor_num + self._analog_num + 16 * self._digital_num) != len(channel_names):
                raise FrameError("Provide CHNAM as list with PHNMR + ANNMR + 16*DGNMR elements.")

            self._channel_names = [channel[:16].ljust(16, " ") for channel in channel_names]

    def get_channel_names(self):

        return self._channel_names

    def set_phasor_units(self, ph_units):
        """
        ### set_phasor_units() ###

        Setter for phasor channels conversion factor.

        **Params:**

        * ``ph_units`` **(list)** - Should be list of tuples ``(scale, phasor_type)``
        where phasor type is ``'i'`` for current and ``'v'`` for voltage.
        If ``multistreaming`` should be list of lists.

        **Raises:**

            FrameError
        When ``ph_units`` is not list of lists with length ``num_pmu`` when ``multistreaming``.
        When ``ph_units`` element is not tuple.

        """

        if self._multistreaming:
            if not all(isinstance(el, list) for el in ph_units) or self._num_pmu != len(ph_units):
                raise FrameError("When NUM_PMU > 1 provide PHUNIT as list of lists.")

            phunit_list = []
            for i, ph_unit in enumerate(ph_units):
                if not all(isinstance(el, tuple) for el in ph_unit) or self._phasor_num[i] != len(ph_unit):
                    raise FrameError("Provide PHUNIT as list of tuples with PHNMR elements. "
                                     "Ex: [(1234,'u'),(1234, 'i')]")

                ph_values = []
                for ph_tuple in ph_unit:
                    ph_values.append(ConfigFrame1._phunit2int(*ph_tuple))

                phunit_list.append(ph_values)

            self._ph_units = phunit_list
        else:
            if not all(isinstance(el, tuple) for el in ph_units) or self._phasor_num != len(ph_units):
                raise FrameError("Provide PHUNIT as list of tuples with PHNMR elements. Ex: [(1234,'u'),(1234, 'i')]")

            self._ph_units = [ConfigFrame1._phunit2int(*phun) for phun in ph_units]

    def get_ph_units(self):

        if all(isinstance(el, list) for el in self._ph_units):
            return [[self._int2phunit(unit) for unit in ph_units] for ph_units in self._ph_units]
        else:
            return [self._int2phunit(ph_unit) for ph_unit in self._ph_units]

    @staticmethod
    def _phunit2int(scale, phasor_type="v"):
        """
        ### phunit2int() ###

        Convert method for phasor channels conversion factor.

        MSB: If phasor type is ``v`` then MSB will be ``0``.
        If phasor type is ``i`` then MSB will be ``1``.

        LSB: Unsigned 24 bit word in 10^-5 V or amperes per bit
        to scale 16-bit integer data.

        If transmitted data is in floating-point format, LSB 24 bit value
        shall be ignored.

        **Params:**

        * ``scale`` **(int)** - scale factor.
        * ``phasor_type`` **(char)** - ``v`` - voltage, ``i`` - current.
        Default value: ``v``.

        **Returns:**

        * ``int`` which represents phasor channels conversion factor.

        **Raises:**

            FrameError
        When ``scale`` is out of range.

        """

        if not 0 <= scale <= 16777215:
            raise ValueError("PHUNIT scale out of range. 0 <= PHUNIT <= 16777215.")

        if phasor_type not in ["v", "i"]:
            raise ValueError("Phasor type should be 'v' or 'i'.")

        if phasor_type == "i":
            phunit = 1 << 24
            return phunit | scale
        else:
            return scale

    @staticmethod
    def _int2phunit(ph_unit):

        phasor_type = ph_unit & 0xff000000
        scale = ph_unit & 0x00ffffff

        if phasor_type > 0:  # Current PH unit
            return scale, "i"
        else:
            return scale, "v"

    def set_analog_units(self, an_units):
        """
        ### set_analog_units() ###

        Setter for analog channels conversion factor.

        **Params:**

        * ``an_units`` **(list)** - Should be list of tuples ``(scale, analog_type)``
        where analog type is ``'pow'`` for single point-on-wave, ``'rms'`` for RMS of
        analog input and ``'peak`` for peak of analog input.
        If ``multistreaming`` should be list of lists.

        **Raises:**

            FrameError
        When ``an_units`` is not list of lists with length ``num_pmu`` when ``multistreaming``.
        When ``an_units`` element is not tuple.

        """

        if self._multistreaming:
            if not all(isinstance(el, list) for el in an_units) or self._num_pmu != len(an_units):
                raise FrameError("When NUM_PMU > 1 provide ANUNIT as list of lists.")

            anunit_list = []
            for i, an_unit in enumerate(an_units):
                if not all(isinstance(el, tuple) for el in an_unit) or self._analog_num[i] != len(an_unit):
                    raise FrameError("Provide ANUNIT as list of tuples with ANNMR elements. "
                                     "Ex: [(1234,'pow'),(1234, 'rms')]")

                an_values = []
                for an_tuple in an_unit:
                    an_values.append(ConfigFrame1._anunit2int(*an_tuple))

                anunit_list.append(an_values)

            self._an_units = anunit_list
        else:
            if not all(isinstance(el, tuple) for el in an_units) or self._analog_num != len(an_units):
                raise FrameError("Provide ANUNIT as list of tuples with ANNMR elements. "
                                 "Ex: [(1234,'pow'),(1234, 'rms')]")

            self._an_units = [ConfigFrame1._anunit2int(*anun) for anun in an_units]

    def get_analog_units(self):

        if all(isinstance(el, list) for el in self._an_units):
            return [[self._int2anunit(unit) for unit in an_unit] for an_unit in self._an_units]
        else:
            return [self._int2anunit(an_unit) for an_unit in self._an_units]

    @staticmethod
    def _anunit2int(scale, anunit_type="pow"):
        """
        ### anunit2int() ###

        Convert method for analog channels conversion factor.

        MSB: If analog type is ``pow`` then MSB will be ``0``.
        If analog type is ``rms`` then MSB will be ``1`` and
        if analog type is ``peak`` then MSB will be ``2``.

        LSB: Signed 24 bit word for user defined scaling.

        **Params:**

        * ``scale`` **(int)** - scale factor.
        * ``anunit_type`` **(char)** - ``pow`` - single point on wave,
        ``rms`` - RMS of analog input and ``peak`` - peak of analog input.
        Also might be user defined. Default value: ``pow``.

        **Returns:**

        * ``int`` which represents analog channels conversion factor.

        **Raises:**

            FrameError
        When ``scale`` is out of range.

        """

        if not -8388608 <= scale <= 8388608:
            raise FrameError("ANUNIT scale out of range. -8388608 <= ANUNIT <=  8388608.")

        scale &= 0xffffff  # 24-bit signed integer

        anunit = 1 << 24

        if anunit_type == "pow":  # TODO: User defined analog units
            anunit |= scale
            return anunit ^ (1 << 24)

        if anunit_type == "rms":
            anunit |= scale
            return anunit

        if anunit_type == "peak":
            anunit |= scale
            return anunit ^ (3 << 24)

    @staticmethod
    def _int2anunit(an_unit):

        TYPES = {"0": "pow", "1": "rms", "2": "peak"}

        an_unit_byte = an_unit.to_bytes(4, byteorder="big", signed=True)
        an_type = int.from_bytes(an_unit_byte[0:1], byteorder="big", signed=False)
        an_scale = int.from_bytes(an_unit_byte[1:4], byteorder="big", signed=True)

        return an_scale, TYPES[str(an_type)]

    def set_digital_units(self, dig_units):
        """
        ### set_digital_units() ###

        Setter for mask words for digital status words.

        Two 16 bit words are provided for each digital word.
        The first will be used to indicate the normal status of the
        digital inputs by returning 0 when XORed with the status word.

        The second will indicate the current valid inputs to the PMU
        by having a bit set in the binary position corresponding to the
         digital input and all other bits set to 0.

        **Params:**

        * ``dig_units`` **(list)** - Should be list of tuples ``(first_mask, second_mask)``.
        If ``multistreaming`` should be list of lists.

        **Raises:**

            FrameError
        When ``dig_units`` is not list of lists with length ``num_pmu`` when ``multistreaming``.
        When ``dig_units`` element is not tuple.

        """

        if self._multistreaming:
            if not all(isinstance(el, list) for el in dig_units) or self._num_pmu != len(dig_units):
                raise FrameError("When NUM_PMU > 1 provide DIGUNIT as list of lists.")

            digunit_list = []
            for i, dig_unit in enumerate(dig_units):
                if not all(isinstance(el, tuple) for el in dig_unit) or self._digital_num[i] != len(dig_unit):
                    raise FrameError("Provide DIGUNIT as list of tuples with DGNMR elements. "
                                     "Ex: [(0x0000,0xffff),(0x0011, 0xff0f)]")

                dig_values = []
                for dig_tuple in dig_unit:
                    dig_values.append(ConfigFrame1._digunit2int(*dig_tuple))

                digunit_list.append(dig_values)

            self._dig_units = digunit_list
        else:
            if not all(isinstance(el, tuple) for el in dig_units) or self._digital_num != len(dig_units):
                raise FrameError("Provide DIGUNIT as list of tuples with DGNMR elements. "
                                 "Ex: [(0x0000,0xffff),(0x0011, 0xff0f)]")

            self._dig_units = [ConfigFrame1._digunit2int(*dgun) for dgun in dig_units]

    def get_digital_units(self):

        if all(isinstance(el, list) for el in self._dig_units):
            return [[self._int2digunit(unit) for unit in dig_unit] for dig_unit in self._dig_units]
        else:
            return [self._int2digunit(dig_unit) for dig_unit in self._dig_units]

    @staticmethod
    def _digunit2int(first_mask, second_mask):
        """
        ### digunit2int() ###

        Generate digital status word mask.

        **Params:**

        * ``first_mask`` **(int)** - status indicator.
        * ``second_mask`` **(int)** - valid input indicator.

        **Returns:**

        * ``int`` which digital status word mask.

        **Raises:**

            FrameError
        When ``first_mask`` is out of range.
        When ``second_mask`` is out of range.

        """

        if not 0 <= first_mask <= 65535:
            raise FrameError("DIGUNIT first mask must be 16-bit word. 0x0000 <= first_mask <= 0xffff")

        if not 0 <= first_mask <= 65535:
            raise FrameError("DIGUNIT second mask must be 16-bit word. 0x0000 <= second_mask <= 0xffff")

        return (first_mask << 16) | second_mask

    @staticmethod
    def _int2digunit(dig_unit):

        first = dig_unit & 0xffff0000
        second = dig_unit & 0x0000ffff

        return first, second

    def set_fnom(self, f_nom):
        """
        ### set_fnom() ###

        Setter for nominal line frequency.

        Should be ``50`` or ``60`` Hz.

        **Params:**

        * ``f_nom`` **(int)** - ``50`` or ``60`` Hz. If ``multistreaming``
        should be list of ints.

        **Raises:**

            FrameError
        When ``f_nom`` is not ``50`` or ``60``.
        When ``f_nom`` is not list of int with length ``num_pmu`` when
        ``multistreaming``.

        """

        if self._multistreaming:
            if not isinstance(f_nom, list) or self._num_pmu != len(f_nom):
                raise FrameError("When NUM_PMU > 1 provide FNOM as list with NUM_PMU elements.")

            fnom_list = []
            for fnom in f_nom:
                fnom_list.append(ConfigFrame1._fnom2int(fnom))

            self._f_nom = fnom_list

        else:
            self._f_nom = ConfigFrame1._fnom2int(f_nom)

    def get_fnom(self):

        if isinstance(self._f_nom, list):
            return [self._int2fnom(fnom) for fnom in self._f_nom]
        else:
            return self._int2fnom(self._f_nom)

    @staticmethod
    def _fnom2int(fnom=60):
        """
        ### fnom2int() ###

        Convert line frequency to code.

        60 Hz = ``0`` and 50 Hz = ``1``.

        **Params:**

        * ``fnom`` **(int)** - Nominal line frequency. Default value: 60.

        **Returns:**

        * ``int`` [``0`` or ``1``]

        **Raises:**

            FrameError
        When ``fnom`` is not 50 or 60.

        """

        if fnom != 50 and fnom != 60:
            raise FrameError("Fundamental frequency must be 50 or 60.")

        if fnom == 50:
            return 1
        else:
            return 0

    @staticmethod
    def _init2fnom(fnom):

        if fnom:
            return 50
        else:
            return 60

    @staticmethod
    def _int2fnom(fnom_int):

        if fnom_int == 0:
            return 60
        else:
            return 50

    def set_cfg_count(self, cfg_count):
        """
        ### set_cfg_count() ###

        Setter for configuration change count.

        Factory default: ``0``. This count will be the number of changes
        of configuration of this message stream.

        **Params:**

        * ``cfg_count`` **(mixed)** - Number of changes. Sholud be list of ints
        if ``multistreaming``.

        **Raises:**

            FrameError.
        When ``cfg_count`` is not list of ints with length ``num_pmu`` when
        ``multistreaming``.
        When ``cfg_count`` is out of range.

        """

        if self._multistreaming:
            if not isinstance(cfg_count, list) or self._num_pmu != len(cfg_count):
                raise FrameError("When NUM_PMU > 1 provide CFGCNT as list with NUM_PMU elements.")

            cfgcnt_list = []
            for cfgcnt in cfg_count:
                if not 0 <= cfgcnt <= 65535:
                    raise FrameError("CFGCNT out of range. 0 <= CFGCNT <= 65535.")
                cfgcnt_list.append(cfgcnt)

            self._cfg_count = cfgcnt_list
        else:
            if not 0 <= cfg_count <= 65535:
                raise FrameError("CFGCNT out of range. 0 <= CFGCNT <= 65535.")
            self._cfg_count = cfg_count

    def get_cfg_count(self):

        return self._cfg_count

    def set_data_rate(self, data_rate):
        """
        ### set_data_rate() ###

        Setter for rate of phasor data transmission.

        If ``data_rate > 0`` rate is number of frames per second.
        If ``data_rate < 0`` rate is negative of seconds per frame.

        **Params:**

        * ``data_rate`` **(int)** - Rate of phasor data transmission.

        **Raises:**

            FrameError.
        When ``data_rate`` is out of range.

        """
        if not -32767 <= data_rate <= 32767:
            raise FrameError("DATA_RATE out of range. -32 767 <= DATA_RATE <= 32 767.")

        self._data_rate = data_rate

    def get_data_rate(self):

        return self._data_rate

    def convert2bytes(self):

        if not self._multistreaming:

            cfg_b = self._time_base.to_bytes(4, "big") + self._num_pmu.to_bytes(2, "big") + \
                str.encode(self._station_name) + self._id_code.to_bytes(2, "big") + \
                self._data_format.to_bytes(2, "big") + self._phasor_num.to_bytes(2, "big") + \
                self._analog_num.to_bytes(2, "big") + self._digital_num.to_bytes(2, "big") + \
                str.encode("".join(self._channel_names)) + list2bytes(self._ph_units, 4) + \
                list2bytes(self._an_units, 4) + list2bytes(self._dig_units, 4) + \
                self._f_nom.to_bytes(2, "big") + self._cfg_count.to_bytes(2, "big") + \
                self._data_rate.to_bytes(2, "big", signed=True)
        else:

            cfg_b = self._time_base.to_bytes(4, "big") + self._num_pmu.to_bytes(2, "big")

            # Concatenate configurations as many as num_pmu tells
            for i in range(self._num_pmu):
                cfg_b_i = str.encode(self._station_name[i]) + self._id_code[i].to_bytes(2, "big") + \
                    self._data_format[i].to_bytes(2, "big") + self._phasor_num[i].to_bytes(2, "big") + \
                    self._analog_num[i].to_bytes(2, "big") + self._digital_num[i].to_bytes(2, "big") + \
                    str.encode("".join(self._channel_names[i])) + list2bytes(self._ph_units[i], 4) + \
                    list2bytes(self._an_units[i], 4) + list2bytes(self._dig_units[i], 4) + \
                    self._f_nom[i].to_bytes(2, "big") + self._cfg_count[i].to_bytes(2, "big")

                cfg_b += cfg_b_i

            cfg_b += self._data_rate.to_bytes(2, "big", signed=True)

        return super().convert2bytes(cfg_b)

    @staticmethod
    def convert2frame(byte_data):

        try:

            if not CommonFrame._check_crc(byte_data):
                raise FrameError("CRC failed. Configuration frame not valid.")

            pmu_code = int.from_bytes(byte_data[4:6], byteorder="big", signed=False)
            soc = int.from_bytes(byte_data[6:10], byteorder="big", signed=False)
            frasec = CommonFrame._int2frasec(int.from_bytes(byte_data[10:14], byteorder="big", signed=False))

            time_base_int = int.from_bytes(byte_data[14:18], byteorder="big", signed=False)
            time_base = time_base_int & 0x00ffffff  # take only first 24 LSB bits

            num_pmu = int.from_bytes(byte_data[18:20], byteorder="big", signed=False)

            start_byte = 20

            if num_pmu > 1:  # Loop through configurations for each

                station_name, id_code, data_format, phasor_num, analog_num, digital_num, channel_names, ph_units, \
                    an_units, dig_units, fnom, cfg_count = [[] for _ in range(12)]

                for i in range(num_pmu):

                    station_name.append(byte_data[start_byte:start_byte + 16].decode("ascii"))
                    start_byte += 16

                    id_code.append(int.from_bytes(byte_data[start_byte:start_byte + 2], byteorder="big", signed=False))
                    start_byte += 2

                    data_format.append(int.from_bytes(byte_data[start_byte:start_byte + 2], byteorder="big", signed=False)
                                       & 0x000f)
                    start_byte += 2

                    phasor_num.append(int.from_bytes(byte_data[start_byte:start_byte + 2], byteorder="big", signed=False))
                    start_byte += 2

                    analog_num.append(int.from_bytes(byte_data[start_byte:start_byte + 2], byteorder="big", signed=False))
                    start_byte += 2

                    digital_num.append(int.from_bytes(byte_data[start_byte:start_byte + 2], byteorder="big", signed=False))
                    start_byte += 2

                    stream_channel_names = []
                    for _ in range(phasor_num[i] + analog_num[i] + 16 * digital_num[i]):
                        stream_channel_names.append(byte_data[start_byte:start_byte + 16].decode("ascii"))
                        start_byte += 16

                    channel_names.append(stream_channel_names)

                    stream_ph_units = []
                    for _ in range(phasor_num[i]):
                        ph_unit = int.from_bytes(byte_data[start_byte:start_byte + 4], byteorder="big", signed=False)
                        stream_ph_units.append(ConfigFrame1._int2phunit(ph_unit))
                        start_byte += 4

                    ph_units.append(stream_ph_units)

                    stream_an_units = []
                    for _ in range(analog_num[i]):
                        an_unit = int.from_bytes(byte_data[start_byte:start_byte + 4], byteorder="big", signed=True)
                        stream_an_units.append(ConfigFrame1._int2anunit(an_unit))
                        start_byte += 4

                    an_units.append(stream_an_units)

                    stream_dig_units = []
                    for _ in range(digital_num[i]):
                        stream_dig_units.append(ConfigFrame1._int2digunit(
                            int.from_bytes(byte_data[start_byte:start_byte + 4], byteorder="big", signed=False)))
                        start_byte += 4

                    dig_units.append(stream_dig_units)

                    fnom.append(ConfigFrame1._int2fnom(int.from_bytes(byte_data[start_byte:start_byte + 2],
                                                                      byteorder="big", signed=False)))
                    start_byte += 2

                    cfg_count.append(int.from_bytes(byte_data[start_byte:start_byte + 2], byteorder="big", signed=False))
                    start_byte += 2

            else:

                station_name = byte_data[start_byte:start_byte + 16].decode("ascii")
                start_byte += 16

                id_code = int.from_bytes(byte_data[start_byte:start_byte + 2], byteorder="big", signed=False)
                start_byte += 2

                data_format_int = int.from_bytes(byte_data[start_byte:start_byte + 2], byteorder="big", signed=False)
                data_format = data_format_int & 0x000f  # Take only first 4 LSB bits
                start_byte += 2

                phasor_num = int.from_bytes(byte_data[start_byte:start_byte + 2], byteorder="big", signed=False)
                start_byte += 2

                analog_num = int.from_bytes(byte_data[start_byte:start_byte + 2], byteorder="big", signed=False)
                start_byte += 2

                digital_num = int.from_bytes(byte_data[start_byte:start_byte + 2], byteorder="big", signed=False)
                start_byte += 2

                channel_names = []
                for _ in range(phasor_num + analog_num + 16 * digital_num):
                    channel_names.append(byte_data[start_byte:start_byte + 16].decode("ascii"))
                    start_byte += 16

                ph_units = []
                for _ in range(phasor_num):
                    ph_unit_int = int.from_bytes(byte_data[start_byte:start_byte + 4], byteorder="big", signed=False)
                    ph_units.append(ConfigFrame1._int2phunit(ph_unit_int))
                    start_byte += 4

                an_units = []
                for _ in range(analog_num):
                    an_unit = int.from_bytes(byte_data[start_byte:start_byte + 4], byteorder="big", signed=False)
                    an_units.append(ConfigFrame1._int2anunit(an_unit))
                    start_byte += 4

                dig_units = []
                for _ in range(digital_num):
                    dig_units.append(ConfigFrame1._int2digunit(
                        int.from_bytes(byte_data[start_byte:start_byte + 4], byteorder="big", signed=False)))
                    start_byte += 4

                fnom = ConfigFrame1._int2fnom(int.from_bytes(byte_data[start_byte:start_byte + 2],
                                                             byteorder="big", signed=False))
                start_byte += 2

                cfg_count = int.from_bytes(byte_data[start_byte:start_byte + 2], byteorder="big", signed=False)
                start_byte += 2

            data_rate = int.from_bytes(byte_data[-4:-2], byteorder="big", signed=True)

            return ConfigFrame1(pmu_code, time_base, num_pmu, station_name, id_code, data_format, phasor_num,
                                analog_num, digital_num, channel_names, ph_units, an_units, dig_units, fnom, cfg_count,
                                data_rate, soc, frasec)

        except Exception as error:
            raise FrameError("Error while creating Config frame: " + str(error))


class ConfigFrame2(ConfigFrame1):
    """
    ## ConfigFrame2 ##

    ConfigFrame2 is class which represents configuration frame v2.
    Carries info about current data stream.

    Class implements two abstract methods from super class.

    * ``convert2bytes()`` - for converting ConfigFrame2 to bytes.
    * ``convert2frame()`` - which converts array of bytes to ConfigFrame2.

    Each instance of ConfigFrame2 class will have following attributes.

    **Attributes:**

    * ``frame_type`` **(int)** - Defines frame type. Inherited from ``CommonFrame``.
    * ``version`` **(int)** - Standard version. Inherited from ``CommonFrame``. Default value: ``1``.
    * ``pmu_id_code`` **(int)** - PMU Id code which identifies data stream. Inherited from ``CommonFrame``.
    * ``soc`` **(int)** - UNIX timestamp. Default value: ``None``. Inherited from ``CommonFrame``.
    * ``frasec`` **(int)** - Fraction of second and Time Quality. Default value: ``None``.
      Inherited from ``CommonFrame``.
    * ``time_base`` **(int)** - Resolution of the fractional second time stamp in all frames.
    * ``num_pmu`` **(int)** - Number of PMUs (data streams) included in single ``DataFrame``.
    * ``multistreaming`` **(bool)** - ``True`` if ``num_pmu > 1``. That means data frame consist of multiple
      measurement streams.
    * ``station_name`` **(mixed)** - Station name ``(string)`` or station names ``(list)`` if ``multistreaming``.
    * ``id_code`` **(mixed)** - Measurement stream ID code ``(int)`` or ``(list)`` if ``multistreaming``. Each ID
      identifies source PMU of each data block.
    * ``data_format`` **(mixed)** - Data format for each data stream. Inherited from ``CommonFrame``.
    * ``phasor_num`` **(mixed)** - Number of phasors ``(int)`` or ``(list)`` if ``multistreaming``.
    * ``analog_num`` **(mixed)** - Number of analog values ``(int)`` or ``(list)`` if ``multistreaming``.
    * ``digital_num`` **(mixed)** - Number of digital status words ``(int)`` or ``(list)`` if ``multistreaming``.
    * ``channel_names`` **(list)** - List of phasor and channel names for phasor, analog and digital channel.
      If ``multistreaming`` it's list of lists.
    * ``ph_units`` **(list)** - Conversion factor for phasor channels. If ``multistreaming`` list of lists.
    * ``an_units`` **(list)** - Conversion factor for analog channels. If ``multistreaming`` list of lists.
    * ``dig_units`` **(list)** - Mask words for digital status word. If ``multistreaming`` list of lists.
    * ``fnom``  **(mixed)** - Nominal frequency code and flags. If ``multistreaming`` list of ints.
    * ``cfg_count`` **(mixed)** - Configuration change count. If ``multistreaming`` list of ints.
    * ``data_rate`` **(int)** - Frames per second or seconds per frame (if negative ``int``).

    **Raises:**

        FrameError
    When it's not possible to create valid frame, usually due invalid parameter value.
    """

    def __init__(self, pmu_id_code, time_base, num_pmu, station_name, id_code, data_format, phasor_num, analog_num,
                 digital_num, channel_names, ph_units, an_units, dig_units, f_nom, cfg_count, data_rate,
                 soc=None, frasec=None, version=1):

        super().__init__(pmu_id_code, time_base, num_pmu, station_name, id_code, data_format, phasor_num, analog_num,
                         digital_num, channel_names, ph_units, an_units, dig_units, f_nom, cfg_count,
                         data_rate, soc, frasec, version)
        super().set_frame_type("cfg2")

    @staticmethod
    def convert2frame(byte_data):

        cfg = ConfigFrame1.convert2frame(byte_data)
        cfg.set_frame_type("cfg2")
        cfg.__class__ = ConfigFrame2  # Casting to derived class

        return cfg


class ConfigFrame3(CommonFrame):
    """
    ## ConfigFrame3 ##

    ConfigFrame3 is class which represents configuration frame v3.

    Class implements two abstract methods from super class.

    * ``convert2bytes()`` - for converting ConfigFrame3 to bytes.
    * ``convert2frame()`` - which converts array of bytes to ConfigFrame3.

    Each instance of ConfigFrame3 class will have following attributes.

    **Attributes:**

    * ``frame_type`` **(int)** - Defines frame type. Inherited from ``CommonFrame``.
    * ``version`` **(int)** - Standard version. Inherited from ``CommonFrame``. Default value: ``1``.
    * ``pmu_id_code`` **(int)** - PMU Id code which identifies data stream. Inherited from ``CommonFrame``.
    * ``soc`` **(int)** - UNIX timestamp. Default value: ``None``. Inherited from ``CommonFrame``.
    * ``frasec`` **(int)** - Fraction of second and Time Quality. Default value: ``None``.
      Inherited from ``CommonFrame``.
    * ``time_base`` **(int)** - Resolution of the fractional second time stamp in all frames.
    * ``num_pmu`` **(int)** - Number of PMUs (data streams) included in single ``DataFrame``.
    * ``multistreaming`` **(bool)** - ``True`` if ``num_pmu > 1``. That means data frame consist of multiple
      measurement streams.
    * ``station_name`` **(mixed)** - Station name ``(string)`` or station names ``(list)`` if ``multistreaming``.
    * ``id_code`` **(mixed)** - Measurement stream ID code ``(int)`` or ``(list)`` if ``multistreaming``. Each ID
      identifies source PMU of each data block.
    * ``data_format`` **(mixed)** - Data format for each data stream. Inherited from ``CommonFrame``.
    * ``phasor_num`` **(mixed)** - Number of phasors ``(int)`` or ``(list)`` if ``multistreaming``.
    * ``analog_num`` **(mixed)** - Number of analog values ``(int)`` or ``(list)`` if ``multistreaming``.
    * ``digital_num`` **(mixed)** - Number of digital status words ``(int)`` or ``(list)`` if ``multistreaming``.
    * ``channel_names`` **(list)** - List of phasor and channel names for phasor, analog and digital channel.
      If ``multistreaming`` it's list of lists.
    * ``ph_units`` **(list)** - Conversion factor for phasor channels. If ``multistreaming`` list of lists.
    * ``an_units`` **(list)** - Conversion factor for analog channels. If ``multistreaming`` list of lists.
    * ``dig_units`` **(list)** - Mask words for digital status word. If ``multistreaming`` list of lists.
    * ``fnom``  **(mixed)** - Nominal frequency code and flags. If ``multistreaming`` list of ints.
    * ``cfg_count`` **(mixed)** - Configuration change count. If ``multistreaming`` list of ints.
    * ``data_rate`` **(int)** - Frames per second or seconds per frame (if negative ``int``).

    **Raises:**

        FrameError
    When it's not possible to create valid frame, usually due invalid parameter value.
    """
    pass  # TODO: Implement Configuration Frame v3


class DataFrame(CommonFrame):

    MEASUREMENT_STATUS = {"ok": 0, "error": 1, "test": 2, "verror": 3}
    MEASUREMENT_STATUS_WORDS = {code: word for word, code in MEASUREMENT_STATUS.items()}

    UNLOCKED_TIME = {"<10": 0, "<100": 1, "<1000": 2, ">1000": 3}
    UNLOCKED_TIME_WORDS = {code: word for word, code in UNLOCKED_TIME.items()}

    TIME_QUALITY = {"n/a": 0, "<100ns": 1, "<1us": 2, "<10us": 3, "<100us": 4, "<1ms": 5, "<10ms": 6, ">10ms": 7}
    TIME_QUALITY_WORDS = {code: word for word, code in TIME_QUALITY.items()}

    TRIGGER_REASON = {"manual": 0, "magnitude_low": 1, "magnitude_high": 2, "phase_angle_diff": 3,
                      "frequency_high_or_log": 4, "df/dt_high": 5, "reserved": 6, "digital": 7}
    TRIGGER_REASON_WORDS = {code: word for word, code in TRIGGER_REASON.items()}

    def __init__(self, pmu_id_code, stat, phasors, freq, dfreq, analog, digital, cfg, soc=None, frasec=None):

        if not isinstance(cfg, ConfigFrame2):
            raise FrameError("CFG should describe current data stream (ConfigurationFrame2)")

        # Common frame for Configuration frame 2 with PMU simulator ID CODE which sends configuration frame.
        super().__init__("data", pmu_id_code, soc, frasec)

        self.cfg = cfg
        self.set_stat(stat)
        self.set_phasors(phasors)
        self.set_freq(freq)
        self.set_dfreq(dfreq)
        self.set_analog(analog)
        self.set_digital(digital)

    def set_stat(self, stat):

        if self.cfg._num_pmu > 1:
            if not isinstance(stat, list) or self.cfg._num_pmu != len(stat):
                raise TypeError("When number of measurements > 1 provide STAT as list with NUM_MEASUREMENTS elements.")

            stats = []  # Format tuples transformed to ints
            for stat_el in stat:
                # If stat is specified as tuple then convert them to int
                if isinstance(stat_el, tuple):
                    stats.append(DataFrame._stat2int(*stat_el))
                else:
                    # If data formats are specified as ints check range
                    if not 0 <= stat_el <= 65536:
                        raise ValueError("STAT out of range. 0 <= STAT <= 65536")
                    else:
                        stats.append(stat_el)

                self._stat = stats
        else:
            if isinstance(stat, tuple):
                self._stat = DataFrame._stat2int(*stat)
            else:
                if not 0 <= stat <= 65536:
                    raise ValueError("STAT out of range. 0 <= STAT <= 65536")
                else:
                    self._stat = stat

    def get_stat(self):

        if isinstance(self._stat, list):
            return [DataFrame._int2stat(stat) for stat in self._stat]
        else:
            return DataFrame._int2stat(self._stat)

    @staticmethod
    def _stat2int(measurement_status="ok", sync=True, sorting="timestamp", trigger=False, cfg_change=False,
                  modified=False, time_quality=5, unlocked="<10", trigger_reason=0):

        if isinstance(measurement_status, str):
            measurement_status = DataFrame.MEASUREMENT_STATUS[measurement_status]

        if isinstance(time_quality, str):
            time_quality = DataFrame.TIME_QUALITY[time_quality]

        if isinstance(unlocked, str):
            unlocked = DataFrame.UNLOCKED_TIME[unlocked]

        if isinstance(trigger_reason, str):
            trigger_reason = DataFrame.TRIGGER_REASON[trigger_reason]

        stat = measurement_status << 2
        if not sync:
            stat |= 1

        stat <<= 1
        if not sorting == "timestamp":
            stat |= 1

        stat <<= 1

        if trigger:
            stat |= 1
        stat <<= 1

        if cfg_change:
            stat |= 1

        stat <<= 1

        if modified:
            stat |= 1

        stat <<= 3
        stat |= time_quality
        stat <<= 2

        stat |= unlocked
        stat <<= 4

        return stat | trigger_reason

    @staticmethod
    def _int2stat(stat):

        measurement_status = DataFrame.MEASUREMENT_STATUS_WORDS[stat >> 15]
        sync = bool(stat & 0x2000)

        if stat & 0x1000:
            sorting = "arrival"
        else:
            sorting = "timestamp"

        trigger = bool(stat & 0x800)
        cfg_change = bool(stat & 0x400)
        modified = bool(stat & 0x200)

        time_quality = DataFrame.TIME_QUALITY_WORDS[stat & 0x1c0]
        unlocked = DataFrame.UNLOCKED_TIME_WORDS[stat & 0x30]
        trigger_reason = DataFrame.TRIGGER_REASON_WORDS[stat & 0xf]

        return measurement_status, sync, sorting, trigger, cfg_change, modified, time_quality, unlocked, trigger_reason

    def set_phasors(self, phasors):

        phasors_list = []  # Format tuples transformed to ints
        if self.cfg._num_pmu > 1:
            if not isinstance(phasors, list) or self.cfg._num_pmu != len(phasors):
                raise TypeError("When number of measurements > 1 provide PHASORS as list of tuple list with "
                                "NUM_MEASUREMENTS elements.")

            if not isinstance(self.cfg._data_format, list) or self.cfg._num_pmu != len(self.cfg._data_format):
                raise TypeError("When number of measurements > 1 provide DATA_FORMAT as list with "
                                "NUM_MEASUREMENTS elements.")

            for i, phasor in enumerate(phasors):

                if not isinstance(phasor, list) or self.cfg._phasor_num[i] != len(phasor):
                    raise TypeError("Provide PHASORS as list of tuples with PHASOR_NUM tuples")

                ph_measurements = []
                for phasor_measurement in phasor:
                    ph_measurements.append(DataFrame._phasor2int(phasor_measurement, self.cfg._data_format[i]))

                phasors_list.append(ph_measurements)
        else:

            if not isinstance(phasors, list) or self.cfg._phasor_num != len(phasors):
                raise TypeError("Provide PHASORS as list of tuples with PHASOR_NUM tuples")

            for phasor_measurement in phasors:
                phasors_list.append(DataFrame._phasor2int(phasor_measurement, self.cfg._data_format))

        self._phasors = phasors_list

    def get_phasors(self, convert2polar=True):

        if all(isinstance(el, list) for el in self._phasors):

            phasors = [[DataFrame._int2phasor(ph, self.cfg._data_format[i]) for ph in phasor]
                       for i, phasor in enumerate(self._phasors)]

            if convert2polar:
                for i, stream_phasors in enumerate(phasors):

                    if not self.cfg.get_data_format()[i][1]:  # If not float representation scale back
                        stream_phasors = [tuple([ph * self.cfg.get_ph_units()[i][j][0] * 0.00001 for ph in phasor])
                                          for j, phasor in enumerate(stream_phasors)]

                        phasors[i] = stream_phasors

                    if not self.cfg.get_data_format()[i][0]:  # If not polar convert to polar representation
                        stream_phasors = [(sqrt(ph[0]**2 + ph[1]**2), atan2(ph[1], ph[0])) for ph in stream_phasors]
                        phasors[i] = stream_phasors
        else:
            phasors = [DataFrame._int2phasor(phasor, self.cfg._data_format) for phasor in self._phasors]

            if not self.cfg.get_data_format()[1]:  # If not float representation scale back
                phasors = [tuple([ph * self.cfg.get_ph_units()[i][0] * 0.00001 for ph in phasor])
                           for i, phasor in enumerate(phasors)]

            if not self.cfg.get_data_format()[0]:  # If not polar convert to polar representation
                phasors = [(sqrt(ph[0]**2 + ph[1]**2), atan2(ph[1], ph[0])) for ph in phasors]

        return phasors

    @staticmethod
    def _phasor2int(phasor, data_format):

        if not isinstance(phasor, tuple):
            raise TypeError("Provide phasor measurement as tuple. Rectangular - (Re, Im); Polar - (Mg, An).")

        if isinstance(data_format, int):
            data_format = DataFrame._int2format(data_format)

        if data_format[0]:  # Polar representation

            if data_format[1]:  # Floating Point

                if not -3.142 <= phasor[1] <= 3.142:
                    raise ValueError("Angle must be in range -3.14 <= ANGLE <= 3.14")

                mg = pack("!f", float(phasor[0]))
                an = pack("!f", float(phasor[1]))
                measurement = mg + an

            else:  # Polar 16-bit representations

                if not 0 <= phasor[0] <= 65535:
                    raise ValueError("Magnitude must be 16-bit unsigned integer. 0 <= MAGNITUDE <= 65535.")

                if not -31416 <= phasor[1] <= 31416:
                    raise ValueError("Angle must be 16-bit signed integer in radians x (10^-4). "
                                     "-31416 <= ANGLE <= 31416.")

                mg = pack("!H", phasor[0])
                an = pack("!h", phasor[1])
                measurement = mg + an

        else:

            if data_format[1]:  # Rectangular floating point representation

                re = pack("!f", float(phasor[0]))
                im = pack("!f", float(phasor[1]))
                measurement = re + im

            else:

                if not ((-32767 <= phasor[0] <= 32767) or (-32767 <= phasor[1] <= 32767)):
                    raise ValueError("Real and imaginary value must be 16-bit signed integers. "
                                     "-32767 <= (Re,Im) <= 32767.")

                re = pack("!h", phasor[0])
                im = pack("!h", phasor[1])
                measurement = re + im

        return int.from_bytes(measurement, "big", signed=False)

    @staticmethod
    def _int2phasor(phasor, data_format):

        if isinstance(data_format, int):
            data_format = DataFrame._int2format(data_format)

        if data_format[1]:  # Float representation
            phasor = unpack("!ff", phasor.to_bytes(8, "big", signed=False))
        elif data_format[0]:  # Polar integer
            phasor = unpack("!Hh", phasor.to_bytes(4, "big", signed=False))
        else:  # Rectangular integer
            phasor = unpack("!hh", phasor.to_bytes(4, "big", signed=False))

        return phasor

    def set_freq(self, freq):

        if self.cfg._num_pmu > 1:
            if not isinstance(freq, list) or self.cfg._num_pmu != len(freq):
                raise TypeError("When number of measurements > 1 provide FREQ as list with "
                                "NUM_MEASUREMENTS elements.")

            if not isinstance(self.cfg._data_format, list) or self.cfg._num_pmu != len(self.cfg._data_format):
                raise TypeError("When number of measurements > 1 provide DATA_FORMAT as list with "
                                "NUM_MEASUREMENTS elements.")

            freq_list = []  # Format tuples transformed to ints
            for i, fr in enumerate(freq):
                freq_list.append(DataFrame._freq2int(fr, self.cfg._data_format[i]))

            self._freq = freq_list
        else:
            self._freq = DataFrame._freq2int(freq, self.cfg._data_format)

    def get_freq(self):

        if isinstance(self._freq, list):
            freq = [DataFrame._int2freq(fr, self.cfg._data_format[i]) for i, fr in enumerate(self._freq)]
        else:
            freq = DataFrame._int2freq(self._freq, self.cfg._data_format)

        return freq

    def _freq2int(freq, data_format):

        if isinstance(data_format, int):
            data_format = DataFrame._int2format(data_format)

        if data_format[3]:  # FREQ/DFREQ floating point
            if not 60. - 32.767 <= freq <= 60. + 32.767:
                raise ValueError("FREQ must be in range -32.767 <= FREQ <= 32.767.")

            freq = unpack("!I", pack("!f", float(freq)))[0]
        else:
            if not -32767 <= freq <= 32767:
                raise ValueError("FREQ must be 16-bit signed integer. -32767 <= FREQ <= 32767.")
            freq = unpack("!H", pack("!h", freq))[0]

        return freq

    def _int2freq(freq, data_format):

        if isinstance(data_format, int):
            data_format = DataFrame._int2format(data_format)

        if data_format[3]:  # FREQ/DFREQ floating point
            freq = unpack("!f", pack("!I", freq))[0]
        else:
            freq = unpack("!h", pack("!H", freq))[0]

        return freq

    def set_dfreq(self, dfreq):

        if self.cfg._num_pmu > 1:
            if not isinstance(dfreq, list) or self.cfg._num_pmu != len(dfreq):
                raise TypeError("When number of measurements > 1 provide DFREQ as list with "
                                "NUM_MEASUREMENTS elements.")

            if not isinstance(self.cfg._data_format, list) or self.cfg._num_pmu != len(self.cfg._data_format):
                raise TypeError("When number of measurements > 1 provide DATA_FORMAT as list with "
                                "NUM_MEASUREMENTS elements.")

            dfreq_list = []  # Format tuples transformed to ints
            for i, dfr in enumerate(dfreq):
                dfreq_list.append(DataFrame._dfreq2int(dfr, self.cfg._data_format[i]))

            self._dfreq = dfreq_list
        else:
            self._dfreq = DataFrame._dfreq2int(dfreq, self.cfg._data_format)

    def get_dfreq(self):

        if isinstance(self._dfreq, list):
            dfreq = [DataFrame._int2dfreq(dfr, self.cfg._data_format[i]) for i, dfr in enumerate(self._dfreq)]
        else:
            dfreq = DataFrame._int2dfreq(self._dfreq, self.cfg._data_format)

        return dfreq

    def _dfreq2int(dfreq, data_format):

        if isinstance(data_format, int):
            data_format = DataFrame._int2format(data_format)

        if data_format[3]:  # FREQ/DFREQ floating point
            dfreq = unpack("!I", pack("!f", float(dfreq)))[0]
        else:
            if not -32767 <= dfreq <= 32767:
                raise ValueError("DFREQ must be 16-bit signed integer. -32767 <= DFREQ <= 32767.")
            dfreq = unpack("!H", pack("!h", dfreq))[0]

        return dfreq

    def _int2dfreq(dfreq, data_format):

        if isinstance(data_format, int):
            data_format = DataFrame._int2format(data_format)

        if data_format[3]:  # FREQ/DFREQ floating point
            dfreq = unpack("!f", pack("!I", dfreq))[0]
        else:
            dfreq = unpack("!h", pack("!H", dfreq))[0]

        return dfreq

    def set_analog(self, analog):

        analog_list = []
        # Format tuples transformed to ints
        if self.cfg._num_pmu > 1:
            if not isinstance(analog, list) or self.cfg._num_pmu != len(analog):
                raise TypeError("When number of measurements > 1 provide ANALOG as list of list with "
                                "NUM_MEASUREMENTS elements.")

            if not isinstance(self.cfg._data_format, list) or self.cfg._num_pmu != len(self.cfg._data_format):
                raise TypeError("When number of measurements > 1 provide DATA_FORMAT as list with "
                                "NUM_MEASUREMENTS elements.")

            for i, an in enumerate(analog):

                if not isinstance(an, list) or self.cfg._analog_num[i] != len(an):
                    raise TypeError("Provide ANALOG as list with ANALOG_NUM elements")

                an_measurements = []
                for analog_measurement in an:
                    an_measurements.append(DataFrame._analog2int(analog_measurement, self.cfg._data_format[i]))

                analog_list.append(an_measurements)

        else:

            if not isinstance(analog, list) or self.cfg._analog_num != len(analog):
                raise TypeError("Provide ANALOG as list with ANALOG_NUM elements")

            for analog_measurement in analog:
                analog_list.append(DataFrame._analog2int(analog_measurement, self.cfg._data_format))

        self._analog = analog_list

    def get_analog(self):

        if all(isinstance(el, list) for el in self._analog):
            analog = [[DataFrame._int2analog(an, self.cfg._data_format[i]) for an in analog]
                      for i, analog in enumerate(self._analog)]
        else:
            analog = [DataFrame._int2analog(an, self.cfg._data_format) for an in self._analog]

        return analog

    def _analog2int(analog, data_format):

        if isinstance(data_format, int):
            data_format = DataFrame._int2format(data_format)

        if data_format[2]:  # ANALOG float
            analog = unpack("!I", pack("!f", float(analog)))[0]
        else:
            # User defined ranges - but fit in 16-bit (u)signed integer
            if not -32767 <= analog <= 32767:
                raise ValueError("ANALOG must be in range -32767 <= FREQ <= 65535.")
            analog = unpack("!H", pack("!h", analog))[0]

        return analog

    def _int2analog(analog, data_format):

        if isinstance(data_format, int):
            data_format = DataFrame._int2format(data_format)

        if data_format[2]:  # ANALOG float
            analog = unpack("!f", pack("!I", analog))[0]
        else:
            analog = unpack("!h", pack("!H", analog))[0]

        return analog

    def set_digital(self, digital):

        digital_list = []
        # Format tuples transformed to ints
        if self.cfg._num_pmu > 1:
            if not isinstance(digital, list) or self.cfg._num_pmu != len(digital):
                raise TypeError("When number of measurements > 1 provide DIGITAL as list of lists with "
                                "NUM_MEASUREMENTS elements.")

            for i, dig in enumerate(digital):

                if not isinstance(dig, list) or self.cfg._digital_num[i] != len(dig):
                    raise TypeError("Provide DIGITAL as list with DIGITAL_NUM elements")

                dig_measurements = []
                for digital_measurement in dig:
                    dig_measurements.append(DataFrame._digital2int(digital_measurement))

                digital_list.append(dig_measurements)

        else:

            if not isinstance(digital, list) or self.cfg._digital_num != len(digital):
                raise TypeError("Provide DIGITAL as list with DIGITAL_NUM elements")

            for digital_measurement in digital:
                digital_list.append(DataFrame._digital2int(digital_measurement))

        self._digital = digital_list

    def get_digital(self):

        return self._digital

    def _digital2int(digital):

        if not -32767 <= digital <= 65535:
            raise ValueError("DIGITAL must be 16 bit word. -32767 <= DIGITAL <= 65535.")
        return unpack("!H", pack("!H", digital))[0]

    def get_measurements(self):

        measurements = []

        if self.cfg._num_pmu > 1:

            frequency = [self.cfg.get_fnom()[i] + freq / 1000 for i, freq in enumerate(self.get_freq())]

            for i in range(self.cfg._num_pmu):

                measurement = {"stream_id": self.cfg.get_stream_id_code()[i],
                               "stat": self.get_stat()[i][0],
                               "phasors": self.get_phasors()[i],
                               "analog": self.get_analog()[i],
                               "digital": self.get_digital()[i],
                               "frequency": self.cfg.get_fnom()[i] + self.get_freq()[i] / 1000,
                               "rocof": self.get_dfreq()[i]}

                measurements.append(measurement)
        else:

            measurements.append({"stream_id": self.cfg.get_stream_id_code(),
                                 "stat": self.get_stat()[0],
                                 "phasors": self.get_phasors(),
                                 "analog": self.get_analog(),
                                 "digital": self.get_digital(),
                                 "frequency": self.cfg.get_fnom() + self.get_freq() / 1000,
                                 "rocof": self.get_dfreq()
                                 })

        data_frame = {"pmu_id": self._pmu_id_code,
                      "time": self.get_soc() + self.get_frasec()[0] / self.cfg.get_time_base(),
                      "measurements": measurements}

        return data_frame

    def convert2bytes(self):

        # Convert DataFrame message to bytes
        if not self.cfg._num_pmu > 1:

            data_format_size = CommonFrame._get_data_format_size(self.cfg._data_format)

            df_b = self._stat.to_bytes(2, "big") + list2bytes(self._phasors, data_format_size["phasor"]) + \
                self._freq.to_bytes(data_format_size["freq"], "big") + \
                self._dfreq.to_bytes(data_format_size["freq"], "big") + \
                list2bytes(self._analog, data_format_size["analog"]) + list2bytes(self._digital, 2)
        else:
            # Concatenate measurements as many as num_measurements tells
            df_b = None
            for i in range(self.cfg._num_pmu):

                data_format_size = CommonFrame._get_data_format_size(self.cfg._data_format[i])

                df_b_i = self._stat[i].to_bytes(2, "big") + \
                    list2bytes(self._phasors[i], data_format_size["phasor"]) + \
                    self._freq[i].to_bytes(data_format_size["freq"], "big") + \
                    self._dfreq[i].to_bytes(data_format_size["freq"], "big") + \
                    list2bytes(self._analog[i], data_format_size["analog"]) + \
                    list2bytes(self._digital[i], 2)

                if df_b:
                    df_b += df_b_i
                else:
                    df_b = df_b_i

        return super().convert2bytes(df_b)

    @staticmethod
    def convert2frame(byte_data, cfg):

        try:

            if not CommonFrame._check_crc(byte_data):
                raise FrameError("CRC failed. Configuration frame not valid.")

            num_pmu = cfg.get_num_pmu()
            data_format = cfg.get_data_format()
            phasor_num = cfg.get_phasor_num()
            analog_num = cfg.get_analog_num()
            digital_num = cfg.get_digital_num()

            pmu_code = int.from_bytes(byte_data[4:6], byteorder="big", signed=False)
            soc = int.from_bytes(byte_data[6:10], byteorder="big", signed=False)
            frasec = CommonFrame._int2frasec(int.from_bytes(byte_data[10:14], byteorder="big", signed=False))

            start_byte = 14

            if num_pmu > 1:

                stat, phasors, freq, dfreq, analog, digital = [[] for _ in range(6)]

                for i in range(num_pmu):

                    st = DataFrame._int2stat(int.from_bytes(byte_data[start_byte:start_byte + 2],
                                                            byteorder="big", signed=False))
                    stat.append(st)
                    start_byte += 2

                    phasor_size = 8 if data_format[i][1] else 4
                    stream_phasors = []
                    for _ in range(phasor_num[i]):
                        phasor = DataFrame._int2phasor(int.from_bytes(byte_data[start_byte:start_byte + phasor_size],
                                                                      byteorder="big", signed=False), data_format[i])
                        stream_phasors.append(phasor)
                        start_byte += phasor_size
                    phasors.append(stream_phasors)

                    freq_size = 4 if data_format[i][3] else 2
                    stream_freq = DataFrame._int2freq(int.from_bytes(byte_data[start_byte:start_byte + freq_size],
                                                                     byteorder="big", signed=False), data_format[i])
                    start_byte += freq_size
                    freq.append(stream_freq)

                    stream_dfreq = DataFrame._int2dfreq(int.from_bytes(byte_data[start_byte:start_byte + freq_size],
                                                                       byteorder="big", signed=False), data_format[i])
                    start_byte += freq_size
                    dfreq.append(stream_dfreq)

                    analog_size = 4 if data_format[i][2] else 2
                    stream_analog = []
                    for _ in range(analog_num[i]):
                        an = DataFrame._int2analog(int.from_bytes(byte_data[start_byte:start_byte + analog_size],
                                                                  byteorder="big", signed=False), data_format[i])
                        stream_analog.append(an)
                        start_byte += analog_size
                    analog.append(stream_analog)

                    stream_digital = []
                    for _ in range(digital_num[i]):
                        dig = int.from_bytes(byte_data[start_byte:start_byte + 2], byteorder="big", signed=False)
                        stream_digital.append(dig)
                        start_byte += 2
                    digital.append(stream_digital)
            else:

                stat = DataFrame._int2stat(int.from_bytes(byte_data[start_byte:start_byte + 2],
                                                          byteorder="big", signed=False))
                start_byte += 2

                phasor_size = 8 if data_format[1] else 4
                phasors = []
                for _ in range(phasor_num):
                    phasor = DataFrame._int2phasor(int.from_bytes(byte_data[start_byte:start_byte + phasor_size],
                                                                  byteorder="big", signed=False), data_format)
                    phasors.append(phasor)
                    start_byte += phasor_size

                freq_size = 4 if data_format[3] else 2
                freq = DataFrame._int2freq(int.from_bytes(byte_data[start_byte:start_byte + freq_size],
                                                          byteorder="big", signed=False), data_format)
                start_byte += freq_size

                dfreq = DataFrame._int2dfreq(int.from_bytes(byte_data[start_byte:start_byte + freq_size], byteorder="big",
                                                            signed=False), data_format)
                start_byte += freq_size

                analog_size = 4 if data_format[2] else 2
                analog = []
                for _ in range(analog_num):
                    an = DataFrame._int2analog(int.from_bytes(byte_data[start_byte:start_byte + analog_size],
                                                              byteorder="big", signed=False), data_format)
                    analog.append(an)
                    start_byte += analog_size

                digital = []
                for _ in range(digital_num):
                    dig = int.from_bytes(byte_data[start_byte:start_byte + 2], byteorder="big", signed=False)
                    digital.append(dig)
                    start_byte += 2

            return DataFrame(pmu_code, stat, phasors, freq, dfreq, analog, digital, cfg, soc, frasec)

        except Exception as error:
            raise FrameError("Error while creating Data frame: " + str(error))


class CommandFrame(CommonFrame):

    COMMANDS = {"stop": 1, "start": 2, "header": 3, "cfg1": 4, "cfg2": 5, "cfg3": 6, "extended": 8}

    # Invert CommandFrame.COMMANDS to get COMMAND_WORDS
    COMMAND_WORDS = {code: word for word, code in COMMANDS.items()}

    def __init__(self, pmu_id_code, command, extended_frame=None, soc=None, frasec=None):

        super().__init__("cmd", pmu_id_code, soc, frasec)

        self.set_command(command)
        self.set_extended_frame(extended_frame)

    def set_command(self, command):

        if command in CommandFrame.COMMANDS:
            self._command = CommandFrame.COMMANDS[command]
        else:
            self._command = CommandFrame._command2int(command)

    def get_command(self):
        return CommandFrame.COMMAND_WORDS[self._command]

    @staticmethod
    def _command2int(command):

        if not 0 <= command <= 65535:
            raise ValueError("Undesignated command code must be 16bit word. 0 <= COMMAND <= 65535")
        else:
            return command

    def set_extended_frame(self, extended_frame):

        if extended_frame is not None:
            self._extended_frame = CommandFrame._extended2int(extended_frame)

    @staticmethod
    def _extended2int(extended_frame):

        if len(extended_frame) > 65518:
            raise ValueError("Extended frame size to large. len(EXTENDED_FRAME) < 65518")
        else:
            return extended_frame

    def convert2bytes(self):

        if self._command == 8:
            cmd_b = self._command.to_bytes(2, "big") + self._extended_frame
        else:
            cmd_b = self._command.to_bytes(2, "big")

        return super().convert2bytes(cmd_b)

    @staticmethod
    def convert2frame(byte_data):

        try:

            if not CommonFrame._check_crc(byte_data):
                raise FrameError("CRC failed. Command frame not valid.")

            pmu_code = int.from_bytes(byte_data[4:6], byteorder="big", signed=False)
            soc = int.from_bytes(byte_data[6:10], byteorder="big", signed=False)
            frasec = CommonFrame._int2frasec(int.from_bytes(byte_data[10:14], byteorder="big", signed=False))

            command_int = int.from_bytes(byte_data[14:16], byteorder="big", signed=False)
            command = [command for command, code in CommandFrame.COMMANDS.items() if code == command_int]

            # Should match only one Command
            if len(command) == 1:
                # Convert list to string
                command = "".join(command)
            else:
                # User defined command
                command = command_int

            # Check if extended frame
            if command == "extended":
                extended_frame = byte_data[16:-2]
            else:
                extended_frame = None

            return CommandFrame(pmu_code, command, extended_frame, soc, frasec)

        except Exception as error:
            raise FrameError("Error while creating Command frame: " + str(error))


class HeaderFrame(CommonFrame):

    def __init__(self, pmu_id_code, header, soc=None, frasec=None):

        super().__init__("header", pmu_id_code, soc, frasec)
        self.set_header(header)

    def set_header(self, header):

        self._header = header

    def get_header(self):

        return self._header

    def convert2bytes(self):

        header_b = str.encode(self._header)
        return super().convert2bytes(header_b)

    @staticmethod
    def convert2frame(byte_data):
        try:

            if not CommonFrame._check_crc(byte_data):
                raise FrameError("CRC failed. Header frame not valid.")

            pmu_code = int.from_bytes(byte_data[4:6], byteorder="big", signed=False)
            soc = int.from_bytes(byte_data[6:10], byteorder="big", signed=False)
            frasec = CommonFrame._int2frasec(int.from_bytes(byte_data[10:14], byteorder="big", signed=False))

            header_message = byte_data[14:-2]
            header_message = str(header_message)

            return HeaderFrame(pmu_code, header_message, soc, frasec)

        except Exception as error:
            raise FrameError("Error while creating Header frame: " + str(error))


class FrameError(BaseException):
    pass
