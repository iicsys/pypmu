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

from abc import ABCMeta, abstractmethod
from synchrophasor.utils import crc16xmodem
from synchrophasor.utils import list2bytes
from struct import pack, unpack
from time import time
import collections

__author__ = "Stevan Sandi"
__copyright__ = "Copyright (c) 2016, Tomo Popovic, Stevan Sandi, Bozo Krstajic"
__credits__ = []
__license__ = "BSD-3"
__version__ = "0.1"


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

    FRAME_TYPES = {'data': 0, 'header': 1, 'cfg1': 2, 'cfg2': 3, 'cfg3': 5, 'cmd': 4}

    # Invert FRAME_TYPES codes to get FRAME_TYPE_WORDS
    FRAME_TYPES_WORDS = {code: word for word, code in FRAME_TYPES.items()}

    def __init__(self, frame_type, pmu_id_code, soc=None, frasec=None, version=1):

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
            self.frame_type = CommonFrame.FRAME_TYPES[frame_type]

    def extract_frame_type(byte_data):
        """This method will only return type of the frame. It shall be used for stream splitter
        since there is no need to create instance of specific frame which will cause lower performance."""

        # Check if frame is valid - using CRC (two last bytes)
        crc_calculated = crc16xmodem(byte_data[0:-2], 0xffff).to_bytes(2, 'big')

        if byte_data[-2:] != crc_calculated:
            raise FrameError("CRC failed. Frame not valid.")

        # Get second byte and determine frame type by shifting right to get higher 4 bits
        frame_type = int.from_bytes([byte_data[1]], byteorder='big', signed=False) >> 4

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
            self.version = version

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
            self.pmu_id_code = id_code

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
            self.set_soc(int())  # Get current timestamp

        if frasec:
            if isinstance(frasec, collections.Sequence):
                self.set_frasec(*frasec)
            else:
                self.set_frasec(frasec)  # Just set fraction of second and use default values for other arguments.
        else:
            # Calculate fraction of second (after decimal point) using only first 7 digits to avoid
            # overflow (24 bit number).
            self.set_frasec(int((((repr((t % 1))).split('.'))[1])[0:6]))

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
            self.soc = soc

    def set_frasec(self, fr_seconds, leap_dir='+', leap_occ=False, leap_pen=False, time_quality=0):
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

        # TODO: Values 12 - 14 are undefined.
        if not 0 <= time_quality <= 15:
                raise FrameError("Time quality flag out of range. 0 <= MSG_TQ <= 15")

        # TODO: Validate leap_dir sign (+ or -).

        frasec = 1 << 1  # Bit 7: Reserved for future use. Not important but it will be 1 for easier byte forming.

        if leap_dir == '-':  # Bit 6: Leap second direction [+ = 0] and [- = 1].
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

        self.frasec = frasec

    def get_data_format_size(data_format):
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

        return {'phasor': phasors_byte_size, 'analog': analog_byte_size, 'freq': freq_byte_size}

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
                    data_formats.append(CommonFrame.format2int(*format_type))
                else:
                    if not 0 <= format_type <= 15:  # If data formats are specified as ints check range
                        raise FrameError("Format Type out of range. 0 <= FORMAT <= 15")
                    else:
                        data_formats.append(format_type)

                self.data_format = data_formats
        else:
            if isinstance(data_format, tuple):
                self.data_format = CommonFrame.format2int(*data_format)
            else:
                if not 0 <= data_format <= 15:
                    raise FrameError("Format Type out of range. 0 <= FORMAT <= 15")
                self.data_format = data_format

    def format2int(phasor_polar=False, phasor_float=False, analogs_float=False, freq_float=False):
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

    @abstractmethod
    def convert2bytes(self, byte_message):

        # SYNC word in CommonFrame starting with AA hex word + frame type + version
        sync_b = (0xaa << 8) | (self.frame_type << 4) | self.version
        sync_b = sync_b.to_bytes(2, 'big')

        # FRAMESIZE: 2B SYNC + 2B FRAMESIZE + 2B IDCODE + 4B SOC + 4B FRASEC + len(Command) + 2B CHK
        frame_size_b = (16 + len(byte_message)).to_bytes(2, 'big')

        # PMU ID CODE
        pmu_id_code_b = self.pmu_id_code.to_bytes(2, 'big')

        # If timestamp not given set timestamp
        if not hasattr(self, 'soc') and not hasattr(self, 'frasec'):
            self.set_time()
        elif not self.soc and not self.frasec:
            self.set_time()

        # SOC
        soc_b = self.soc.to_bytes(4, 'big')

        # FRASEC
        frasec_b = self.frasec.to_bytes(4, 'big')

        # CHK
        crc_chk_b = crc16xmodem(sync_b + frame_size_b + pmu_id_code_b + soc_b + frasec_b + byte_message, 0xffff)

        return sync_b + frame_size_b + pmu_id_code_b + soc_b + frasec_b + byte_message + crc_chk_b.to_bytes(2, 'big')

    @abstractmethod
    def convert2frame(byte_data):

        convert_method = {
            0: DataFrame.convert2frame,
            1: HeaderFrame.convert2frame,
            2: ConfigFrame1.convert2frame,
            3: ConfigFrame2.convert2frame,
            4: CommandFrame.convert2frame,
            5: ConfigFrame3.convert2frame,
        }

        # Check if frame is valid - using CRC (two last bytes)
        crc_calculated = crc16xmodem(byte_data[0:-2], 0xffff).to_bytes(2, 'big')

        if byte_data[-2:] != crc_calculated:
            raise FrameError("CRC failed. Frame not valid.")

        # Get second byte and determine frame type by shifting right to get higher 4 bits
        frame_type = int.from_bytes([byte_data[1]], byteorder='big', signed=False) >> 4

        return convert_method[frame_type](byte_data)


class ConfigFrame(CommonFrame):
    pass


class ConfigFrame1(ConfigFrame):
    """
    ## ConfigFrame1 ##

    ConfigFrame1 is class which represents configuration frame v1.

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
    pass  # TODO: Implement ConfigFrame1


class ConfigFrame2(ConfigFrame):
    """
    ## ConfigFrame2 ##

    ConfigFrame2 is class which represents configuration frame v2.

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

        super().__init__('cfg2', pmu_id_code, soc, frasec, version)  # Init CommonFrame with 'cfg2' frame type

        self.set_time_base(time_base)
        self.set_num_pmu(num_pmu)
        self.set_stn_names(station_name)
        self.set_config_id_code(id_code)
        self.set_data_format(data_format, num_pmu)
        self.set_phasor_num(phasor_num)
        self.set_analog_num(analog_num)
        self.set_digital_num(digital_num)
        self.set_channel_names(channel_names)
        self.set_phasor_unit(ph_units)
        self.set_analog_unit(an_units)
        self.set_digital_unit(dig_units)
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
            self.time_base = time_base

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
            self.num_pmu = num_pmu
            self.multistreaming = True if num_pmu > 1 else False

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

        if self.multistreaming:
            if not isinstance(station_name, list) or self.num_pmu != len(station_name):
                raise FrameError("When NUM_PMU > 1 provide station names as list with NUM_PMU elements.")

            self.station_name = [station[:16].ljust(16, ' ') for station in station_name]
        else:
            self.station_name = station_name[:16].ljust(16, ' ')

    def set_config_id_code(self, id_code):
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

        if self.multistreaming:
            if not isinstance(id_code, list) or self.num_pmu != len(id_code):
                raise FrameError("When NUM_PMU > 1 provide PMU ID codes as list with NUM_PMU elements.")

            for stream_id in id_code:
                if not 1 <= stream_id <= 65534:
                    raise FrameError("ID CODE out of range. 1 <= ID_CODE <= 65534")
        else:
            if not 1 <= id_code <= 65534:
                    raise FrameError("ID CODE out of range. 1 <= ID_CODE <= 65534")

        self.id_code = id_code

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

        if self.multistreaming:
            if not isinstance(phasor_num, list) or self.num_pmu != len(phasor_num):
                raise FrameError("When NUM_PMU > 1 provide PHNMR as list with NUM_PMU elements.")

            for phnmr in phasor_num:
                if not 0 <= phnmr <= 65535:
                    raise FrameError("Number of phasors out of range. 0 <= PHNMR <= 65535")
        else:
            if not 0 <= phasor_num <= 65535:
                    raise FrameError("Number of phasors out of range. 0 <= PHNMR <= 65535")

        self.phasor_num = phasor_num

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

        if self.multistreaming:
            if not isinstance(analog_num, list) or self.num_pmu != len(analog_num):
                raise FrameError("When NUM_PMU > 1 provide ANNMR as list with NUM_PMU elements.")

            for annmr in analog_num:
                if not 0 <= annmr <= 65535:
                    raise FrameError("Number of phasors out of range. 0 <= ANNMR <= 65535")
        else:
            if not 0 <= analog_num <= 65535:
                    raise FrameError("Number of phasors out of range. 0 <= ANNMR <= 65535")

        self.analog_num = analog_num

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
        if self.multistreaming:
            if not isinstance(digital_num, list) or self.num_pmu != len(digital_num):
                raise FrameError("When NUM_PMU > 1 provide DGNMR as list with NUM_PMU elements.")

            for dgnmr in digital_num:
                if not 0 <= dgnmr <= 65535:
                    raise FrameError("Number of phasors out of range. 0 <= DGNMR <= 65535")
        else:
            if not 0 <= digital_num <= 65535:
                    raise FrameError("Number of phasors out of range. 0 <= DGNMR <= 65535")

        self.digital_num = digital_num

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

        if self.multistreaming:
            if not all(isinstance(el, list) for el in channel_names) or self.num_pmu != len(channel_names):
                raise FrameError("When NUM_PMU > 1 provide CHNAM as list of lists with NUM_PMU elements.")

            channel_name_list = []
            for i, chnam in enumerate(channel_names):
                # Channel names must be list with PHNMR + ANNMR + 16*DGNMR elements. Each bit in one digital word
                # (16bit) has it's own label.
                if (self.phasor_num[i] + self.analog_num[i] + 16*self.digital_num[i]) != len(chnam):
                    raise FrameError('Provide CHNAM as list with PHNMR + ANNMR + 16*DGNMR elements for each stream.')
                channel_name_list.append([chn[:16].ljust(16, ' ') for chn in chnam])

            self.channel_names = channel_name_list
        else:
            if not isinstance(channel_names, list) or \
                            (self.phasor_num + self.analog_num + 16*self.digital_num) != len(channel_names):
                raise FrameError("Provide CHNAM as list with PHNMR + ANNMR + 16*DGNMR elements.")

            self.channel_names = [channel[:16].ljust(16, ' ') for channel in channel_names]

    def set_phasor_unit(self, ph_units):
        """
        ### set_phasor_unit() ###

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

        if self.multistreaming:
            if not all(isinstance(el, list) for el in ph_units) or self.num_pmu != len(ph_units):
                raise FrameError("When NUM_PMU > 1 provide PHUNIT as list of lists.")

            phunit_list = []
            for i, ph_unit in enumerate(ph_units):
                if not all(isinstance(el, tuple) for el in ph_unit) or self.phasor_num[i] != len(ph_unit):
                    raise FrameError("Provide PHUNIT as list of tuples with PHNMR elements. "
                                     "Ex: [(1234,'u'),(1234, 'i')]")

                ph_values = []
                for ph_tuple in ph_unit:
                    ph_values.append(ConfigFrame2.phunit2int(*ph_tuple))

                phunit_list.append(ph_values)

            self.ph_units = phunit_list
        else:
            if not all(isinstance(el, tuple) for el in ph_units) or self.phasor_num != len(ph_units):
                raise FrameError("Provide PHUNIT as list of tuples with PHNMR elements. Ex: [(1234,'u'),(1234, 'i')]")

            self.ph_units = [ConfigFrame2.phunit2int(*phun) for phun in ph_units]

    def phunit2int(scale, phasor_type='v'):
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

        if phasor_type == 'i':  # TODO: Check if valid phasor_type
            phunit = 1 << 24
            return phunit | scale
        else:
            return scale

    def set_analog_unit(self, an_units):
        """
        ### set_analog_unit() ###

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

        if self.multistreaming:
            if not all(isinstance(el, list) for el in an_units) or self.num_pmu != len(an_units):
                raise FrameError("When NUM_PMU > 1 provide ANUNIT as list of lists.")

            anunit_list = []
            for i, an_unit in enumerate(an_units):
                if not all(isinstance(el, tuple) for el in an_unit) or self.analog_num[i] != len(an_unit):
                    raise FrameError("Provide ANUNIT as list of tuples with ANNMR elements. "
                                     "Ex: [(1234,'pow'),(1234, 'rms')]")

                an_values = []
                for an_tuple in an_unit:
                    an_values.append(ConfigFrame2.anunit2int(*an_tuple))

                anunit_list.append(an_values)

            self.an_units = anunit_list
        else:
            if not all(isinstance(el, tuple) for el in an_units) or self.analog_num != len(an_units):
                raise FrameError("Provide ANUNIT as list of tuples with ANNMR elements. "
                                 "Ex: [(1234,'pow'),(1234, 'rms')]")

            self.an_units = [ConfigFrame2.anunit2int(*anun) for anun in an_units]

    def anunit2int(scale, anunit_type='pow'):
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

        anunit = 1 << 24

        if anunit_type == 'pow':  # TODO: User defined analog units
            anunit |= scale
            return anunit ^ (1 << 24)

        if anunit_type == 'rms':
            anunit |= scale
            return anunit

        if anunit_type == 'peak':
            anunit |= scale
            return anunit ^ (3 << 24)

    def set_digital_unit(self, dig_units):
        """
        ### set_digital_unit() ###

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

        if self.multistreaming:
            if not all(isinstance(el, list) for el in dig_units) or self.num_pmu != len(dig_units):
                raise FrameError("When NUM_PMU > 1 provide DIGUNIT as list of lists.")

            digunit_list = []
            for i, dig_unit in enumerate(dig_units):
                if not all(isinstance(el, tuple) for el in dig_unit) or self.digital_num[i] != len(dig_unit):
                    raise FrameError("Provide DIGUNIT as list of tuples with DGNMR elements. "
                                     "Ex: [(0x0000,0xffff),(0x0011, 0xff0f)]")

                dig_values = []
                for dig_tuple in dig_unit:
                    dig_values.append(ConfigFrame2.digunit2int(*dig_tuple))

                digunit_list.append(dig_values)

            self.dig_units = digunit_list
        else:
            if not all(isinstance(el, tuple) for el in dig_units) or self.digital_num != len(dig_units):
                raise FrameError("Provide DIGUNIT as list of tuples with DGNMR elements. "
                                 "Ex: [(0x0000,0xffff),(0x0011, 0xff0f)]")

            self.dig_units = [ConfigFrame2.digunit2int(*dgun) for dgun in dig_units]

    def digunit2int(first_mask, second_mask):
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

        if self.multistreaming:
            if not isinstance(f_nom, list) or self.num_pmu != len(f_nom):
                raise FrameError("When NUM_PMU > 1 provide FNOM as list with NUM_PMU elements.")

            fnom_list = []
            for fnom in f_nom:
                fnom_list.append(ConfigFrame2.fnom2int(fnom))

            self.f_nom = fnom_list

        else:
            self.f_nom = ConfigFrame2.fnom2int(f_nom)

    def fnom2int(fnom=60):
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

        if self.multistreaming:
            if not isinstance(cfg_count, list) or self.num_pmu != len(cfg_count):
                raise FrameError("When NUM_PMU > 1 provide CFGCNT as list with NUM_PMU elements.")

            cfgcnt_list = []
            for cfgcnt in cfg_count:
                if not 0 <= cfgcnt <= 65535:
                    raise FrameError("CFGCNT out of range. 0 <= CFGCNT <= 65535.")
                cfgcnt_list.append(cfgcnt)

            self.cfg_count = cfgcnt_list
        else:
            if not 0 <= cfg_count <= 65535:
                    raise FrameError("CFGCNT out of range. 0 <= CFGCNT <= 65535.")
            self.cfg_count = cfg_count

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
        self.data_rate = data_rate

    def convert2bytes(self):

        if not self.multistreaming:

            cfg_b = self.time_base.to_bytes(4, 'big') + self.num_pmu.to_bytes(2, 'big') + \
                        str.encode(self.station_name) + self.id_code.to_bytes(2, 'big') + \
                        self.data_format.to_bytes(2, 'big') + self.phasor_num.to_bytes(2, 'big') + \
                        self.analog_num.to_bytes(2, 'big') + self.digital_num.to_bytes(2, 'big') + \
                        str.encode(''.join(self.channel_names)) + list2bytes(self.ph_units, 4) + \
                        list2bytes(self.an_units, 4) + list2bytes(self.dig_units, 4) + \
                        self.f_nom.to_bytes(2, 'big') + self.cfg_count.to_bytes(2, 'big') + \
                        self.data_rate.to_bytes(2, 'big')
        else:

            cfg_b = self.time_base.to_bytes(4, 'big') + self.num_pmu.to_bytes(2, 'big')

            # Concatenate configurations as many as num_pmu tells
            for i in range(self.num_pmu):

                cfg_b_i = str.encode(self.station_name[i]) + self.id_code[i].to_bytes(2, 'big') + \
                          self.data_format[i].to_bytes(2, 'big') + self.phasor_num[i].to_bytes(2, 'big') + \
                          self.analog_num[i].to_bytes(2, 'big') + self.digital_num[i].to_bytes(2, 'big') + \
                          str.encode(''.join(self.channel_names[i])) + list2bytes(self.ph_units[i], 4) +\
                          list2bytes(self.an_units[i], 4) + list2bytes(self.dig_units[i], 4) + \
                          self.f_nom[i].to_bytes(2, 'big') + self.cfg_count[i].to_bytes(2, 'big')

                cfg_b += cfg_b_i

            cfg_b += self.data_rate.to_bytes(2, 'big')

        return super().convert2bytes(cfg_b)

    @staticmethod
    def convert2frame(byte_data):
        return byte_data


class ConfigFrame3(ConfigFrame):
    """
    ## ConfigFrame3 ##

    ConfigFrame3 is class which represents configuration frame v3.

    Class implements two abstract methods from super class.

    * ``convert2bytes()`` - for converting ConfigFrame3 to bytes.
    * ``convert2frame()`` - which converts array of bytes to ConfigFrame3.

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
    pass  # TODO: Implement Configuration Frame v3


class DataFrame(CommonFrame):

    MEASUREMENT_STATUS = {'ok': 0, 'error': 1, 'test': 2, 'verror': 3}
    UNLOCKED_TIME = {'<10': 0, '<100': 1, '<1000': 2, '>1000': 3}

    def __init__(self, pmu_id_code, stat, phasors, freq, dfreq, analog, digital, data_format, num_measurements=1,
                 soc=None, frasec=None):

        # Common frame for Configuration frame 2 with PMU simulator ID CODE which sends configuration frame.
        super().__init__('data', pmu_id_code, soc, frasec)

        # TODO: ValueError for this
        self.num_measurements = num_measurements
        self.set_data_format(data_format, num_measurements)
        self.set_stat(stat)
        self.set_phasors(phasors)
        self.set_freq(freq)
        self.set_dfreq(dfreq)
        self.set_analog(analog)
        self.set_digital(digital)

    def set_stat(self, stat):

        if self.num_measurements > 1:
            if not isinstance(stat, list) or self.num_measurements != len(stat):
                raise TypeError("When number of measurements > 1 provide STAT as list with NUM_MEASUREMENTS elements.")

            stats = []  # Format tuples transformed to ints
            for stat_el in stat:
                # If stat is specified as tuple then convert them to int
                if isinstance(stat_el, tuple):
                    stats.append(DataFrame.stat2int(*stat_el))
                else:
                    # If data formats are specified as ints check range
                    if not 0 <= stat_el <= 65536:
                        raise ValueError("STAT out of range. 0 <= STAT <= 65536")
                    else:
                        stats.append(stat_el)

                self.stat = stats
        else:
            if isinstance(stat, tuple):
                self.stat = DataFrame.stat2int(*stat)
            else:
                if not 0 <= stat <= 65536:
                    raise ValueError("STAT out of range. 0 <= STAT <= 65536")
                else:
                    self.stat = stat

    # STAT: TODO: Document Table 7. and unlocked time
    def stat2int(measurement_status='ok', sync = True, sorting='timestamp', trigger=False, cfg_change=False,
                 modified=False, time_quality=5, unlocked='<10', trigger_reason=0):

        stat = DataFrame.MEASUREMENT_STATUS[measurement_status] << 2
        if not sync:
            stat |= 1

        stat <<= 1
        if not sorting == 'timestamp':
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

        stat |= DataFrame.UNLOCKED_TIME[unlocked]
        stat <<= 4

        return stat | trigger_reason

    def set_phasors(self, phasors):

        phasors_list = []  # Format tuples transformed to ints
        if self.num_measurements > 1:
            if not isinstance(phasors, list) or self.num_measurements != len(phasors):
                raise TypeError("When number of measurements > 1 provide PHASORS as list of tuple list with "
                                "NUM_MEASUREMENTS elements.")

            if not isinstance(self.data_format, list) or self.num_measurements != len(self.data_format):
                raise TypeError("When number of measurements > 1 provide DATA_FORMAT as list with "
                                "NUM_MEASUREMENTS elements.")

            for i, phasor in enumerate(phasors):
                ph_measurements = []
                # TODO: Add phasor_num to check length of phasor list
                for phasor_measurement in phasor:
                    ph_measurements.append(DataFrame.phasor2int(phasor_measurement, self.data_format[i]))

                phasors_list.append(ph_measurements)
        else:
            for phasor_measurement in phasors:
                phasors_list.append(DataFrame.phasor2int(phasor_measurement, self.data_format))

        self.phasors = phasors_list

    def phasor2int(phasor, data_format):

        if not isinstance(phasor, tuple):
            raise TypeError("Provide phasor measurement as tuple. Rectangular - (Re, Im); Polar - (Mg, An).")

        # Check if first bit in data_format is 1 -> polar representation else rectangular
        if (data_format & 1) != 0:

            # Check if second bit in data_format is 1 -> floating point representation
            if (data_format & 2) != 0:

                # Polar floating point representation
                # Angle in radians must be between -3.14 to +3.14
                if not -3.15 < phasor[1] < 3.15:
                    raise ValueError("Angle in radians must be between -3.14 and +3.14.")

                mg = pack('!f', float(phasor[0]))
                an = pack('!f', float(phasor[1]))
                measurement = mg + an

                return int.from_bytes(measurement, 'big', signed=False)

            else:
                # Polar 16-bit representations
                if not 0 <= phasor[0] <= 65535:
                    raise ValueError("Magnitude must be 16-bit unsigned integer. 0 <= MAGNITUDE <= 65535.")

                if not -31416 <= phasor[1] <= 31416:
                    raise ValueError("Angle must be 16-bit signed integer in radians x (10^-4). "
                                     "-31416 <= ANGLE <= 31416.")

                return (phasor[0] << 16) | phasor[1]

        else:

            if (data_format & 2) != 0:

                # Rectangular floating point representation
                re = pack('!f', float(phasor[0]))
                im = pack('!f', float(phasor[1]))
                measurement = re + im

                return int.from_bytes(measurement, 'big', signed=False)

            else:

                if not ((-65535 <= phasor[0] <= 65535) or (-65535 <= phasor[1] <= 65535)):
                    raise ValueError("Real and imaginary value must be 16-bit signed integers. "
                                     "-31767 <= (Re,Im) <= 31767.")

                return (phasor[0] << 16) | phasor[1]

    def set_freq(self, freq):

        if self.num_measurements > 1:
            if not isinstance(freq, list) or self.num_measurements != len(freq):
                raise TypeError("When number of measurements > 1 provide FREQ as list with "
                                "NUM_MEASUREMENTS elements.")

            if not isinstance(self.data_format, list) or self.num_measurements != len(self.data_format):
                raise TypeError("When number of measurements > 1 provide DATA_FORMAT as list with "
                                "NUM_MEASUREMENTS elements.")

            freq_list = []  # Format tuples transformed to ints
            for i, fr in enumerate(freq):
                freq_list.append(DataFrame.freq2int(fr, self.data_format[i]))

            self.freq = freq_list
        else:
            self.freq = DataFrame.freq2int(freq, self.data_format)

    def freq2int(freq, data_format):

        # Check if third bit in data_format is 1 -> floating point representation
        if (data_format & 8) != 0:
            return unpack('!I', pack('!f', float(freq)))[0]
        else:
            if not -32767 <= freq <= 32767:
                raise ValueError("FREQ must be 16-bit signed integer. -32767 <= FREQ <= 32767.")
            return freq

    def set_dfreq(self, dfreq):

        if self.num_measurements > 1:
            if not isinstance(dfreq, list) or self.num_measurements != len(dfreq):
                raise TypeError("When number of measurements > 1 provide DFREQ as list with "
                                "NUM_MEASUREMENTS elements.")

            if not isinstance(self.data_format, list) or self.num_measurements != len(self.data_format):
                raise TypeError("When number of measurements > 1 provide DATA_FORMAT as list with "
                                "NUM_MEASUREMENTS elements.")

            dfreq_list = []  # Format tuples transformed to ints
            for i, dfr in enumerate(dfreq):
                dfreq_list.append(DataFrame.dfreq2int(dfr, self.data_format[i]))

            self.dfreq = dfreq_list
        else:
            self.dfreq = DataFrame.dfreq2int(dfreq, self.data_format)

    def dfreq2int(dfreq, data_format):

        # Check if third bit in data_format is 1 -> floating point representation
        if (data_format & 8) != 0:
            return unpack('!I', pack('!f', float(dfreq)))[0]
        else:
            if not -32767 <= dfreq <= 32767:
                raise ValueError("DFREQ must be 16-bit signed integer. -32767 <= FREQ <= 32767.")
            return dfreq

    def set_analog(self, analog):

        analog_list = []
        # Format tuples transformed to ints
        if self.num_measurements > 1:
            if not isinstance(analog, list) or self.num_measurements != len(analog):
                raise TypeError("When number of measurements > 1 provide ANALOG as list of list with "
                                "NUM_MEASUREMENTS elements.")

            if not isinstance(self.data_format, list) or self.num_measurements != len(self.data_format):
                raise TypeError("When number of measurements > 1 provide DATA_FORMAT as list with "
                                "NUM_MEASUREMENTS elements.")

            for i, an in enumerate(analog):
                an_measurements = []
                # TODO: Add analog_num to check length of analog list
                for analog_measurement in an:
                    an_measurements.append(DataFrame.analog2int(analog_measurement, self.data_format[i]))

                analog_list.append(an_measurements)

        else:
            for analog_measurement in analog:
                analog_list.append(DataFrame.analog2int(analog_measurement, self.data_format))

        self.analog = analog_list

    def analog2int(analog, data_format):

        # Check if third bit in data_format is 1 -> floating point representation
        if (data_format & 4) != 0:
            return unpack('!I', pack('!f', float(analog)))[0]
        else:
            # User defined ranges - but fit in 16-bit (u)signed integer
            if not -32767 <= analog <= 65535:
                raise ValueError("ANALOG must be 16-bit (u)signed integer. -32767 <= FREQ <= 65535.")
            return analog

    def set_digital(self, digital):

        digital_list = []
        # Format tuples transformed to ints
        if self.num_measurements > 1:
            if not isinstance(digital, list) or self.num_measurements != len(digital):
                raise TypeError("When number of measurements > 1 provide DIGITAL as list of lists with "
                                "NUM_MEASUREMENTS elements.")

            for i, dig in enumerate(digital):
                dig_measurements = []
                # TODO: Add digital_num to check length of dig list
                for digital_measurement in dig:
                    dig_measurements.append(DataFrame.digital2int(digital_measurement))

                digital_list.append(dig_measurements)

        else:
            for digital_measurement in digital:
                digital_list.append(DataFrame.digital2int(digital_measurement))

        self.digital = digital_list

    def digital2int(digital):

        if not -32767 <= digital <= 65535:
            raise ValueError("DIGITAL must be 16 bit word. -32767 <= DIGITAL <= 65535.")
        return digital

    def convert2bytes(self):

        # Convert DataFrame message to bytes
        if not self.num_measurements > 1:

            data_format_size = CommonFrame.get_data_format_size(self.data_format)

            df_b = self.stat.to_bytes(2, 'big') + list2bytes(self.phasors, data_format_size['phasor']) + \
                   self.freq.to_bytes(data_format_size['freq'], 'big') + \
                   self.dfreq.to_bytes(data_format_size['freq'], 'big') + \
                   list2bytes(self.analog, data_format_size['analog']) + list2bytes(self.digital, 2)
        else:
            # Concatenate measurements as many as num_measurements tells
            df_b = None
            for i in range(self.num_measurements):

                data_format_size = CommonFrame.get_data_format_size(self.data_format[i])

                df_b_i = self.stat[i].to_bytes(2, 'big') + \
                         list2bytes(self.phasors[i], data_format_size['phasor']) + \
                         self.freq[i].to_bytes(data_format_size['freq'], 'big') + \
                         self.dfreq[i].to_bytes(data_format_size['freq'], 'big') + \
                         list2bytes(self.analog[i], data_format_size['analog']) + \
                         list2bytes(self.digital[i], 2)

                if df_b:
                    df_b += df_b_i
                else:
                    df_b = df_b_i

        return super().convert2bytes(df_b)

    @staticmethod
    def convert2frame(byte_data):
        return byte_data


class CommandFrame(CommonFrame):

    COMMANDS = {'stop': 1, 'start': 2, 'header': 3, 'cfg1': 4, 'cfg2': 5, 'cfg3': 6, 'extended': 8}

    # Invert CommandFrame.COMMANDS to get COMMAND_WORDS
    COMMAND_WORDS = {code: word for word, code in COMMANDS.items()}

    def __init__(self, pmu_id_code, command, extended_frame=None, soc=None, frasec=None):

        super().__init__('cmd', pmu_id_code, soc, frasec)

        self.set_command(command)
        self.set_extended_frame(extended_frame)

    def set_command(self, command):

        if command in CommandFrame.COMMANDS:
            self.command = CommandFrame.COMMANDS[command]
        else:
            self.command = CommandFrame.command2int(command)

    def get_command(self):
        return CommandFrame.COMMAND_WORDS[self.command]

    def command2int(command):

        if not 0 <= command <= 65535:
            raise ValueError("Undesignated command code must be 16bit word. 0 <= COMMAND <= 65535")
        else:
            return command

    def set_extended_frame(self, extended_frame):

        if extended_frame is not None:
            self.extended_frame = CommandFrame.extended2int(extended_frame)

    def extended2int(extended_frame):

        if len(extended_frame) > 65518:
            raise ValueError("Extended frame size to large. len(EXTENDED_FRAME) < 65518")
        else:
            return extended_frame

    def convert2bytes(self):

        if self.command == 8:
            cmd_b = self.command.to_bytes(2, 'big') + self.extended_frame
        else:
            cmd_b = self.command.to_bytes(2, 'big')

        return super().convert2bytes(cmd_b)

    @staticmethod
    def convert2frame(byte_data):

        try:
            pmu_code = int.from_bytes(byte_data[4:6], byteorder='big', signed=False)
            soc = int.from_bytes(byte_data[6:10], byteorder='big', signed=False)
            time_quality_frasec = int.from_bytes(byte_data[10:11], byteorder='big', signed=False)

            # Get bits using masks
            leap_dir = time_quality_frasec & 0b01000000
            leap_occ = time_quality_frasec & 0b00100000
            leap_pen = time_quality_frasec & 0b00010000

            time_quality = time_quality_frasec & 0b00001111

            # Reassign values to create Command frame
            leap_dir = '-' if leap_dir else '+'
            leap_occ = bool(leap_occ)
            leap_pen = bool(leap_pen)

            frasec = int.from_bytes(byte_data[11:14], byteorder='big', signed=False)

            command_int = int.from_bytes(byte_data[14:16], byteorder='big', signed=False)
            command = [command for command, code in CommandFrame.COMMANDS.items() if code == command_int]

            # Should match only one Command
            if len(command) == 1:
                # Convert list to string
                command = ''.join(command)
            else:
                # User defined command
                command = command_int

            # Check if extended frame
            if command == 'extended':
                extended_frame = byte_data[16:-2]
            else:
                extended_frame = None

            return CommandFrame(pmu_code, command, extended_frame, soc, (frasec, leap_dir, leap_occ,
                                                                         leap_pen, time_quality))

        except Exception as error:
            raise FrameError("Error while creating Command frame: " + str(error))


class HeaderFrame(CommonFrame):

    def __init__(self, pmu_id_code, header, soc=None, frasec=None):

        super().__init__('header', pmu_id_code, soc, frasec)
        self.header = header

    def convert2bytes(self):

        header_b = str.encode(self.header)
        return super().convert2bytes(header_b)

    @staticmethod
    def convert2frame(byte_data):
        try:
            pmu_code = int.from_bytes(byte_data[4:6], byteorder='big', signed=False)
            soc = int.from_bytes(byte_data[6:10], byteorder='big', signed=False)
            time_quality_frasec = int.from_bytes(byte_data[10:11], byteorder='big', signed=False)

            # Get bits using masks
            leap_dir = time_quality_frasec & 0b01000000
            leap_occ = time_quality_frasec & 0b00100000
            leap_pen = time_quality_frasec & 0b00010000

            time_quality = time_quality_frasec & 0b00001111

            # Reassign values to create Command frame
            leap_dir = '-' if leap_dir else '+'
            leap_occ = bool(leap_occ)
            leap_pen = bool(leap_pen)

            frasec = int.from_bytes(byte_data[11:14], byteorder='big', signed=False)

            header_message = byte_data[14:-2]
            header_message = str(header_message)

            return HeaderFrame(pmu_code, header_message, soc, (frasec, leap_dir, leap_occ, leap_pen,
                                                               time_quality))

        except Exception as error:
            raise FrameError("Error while creating Header frame: " + str(error))


class FrameError(BaseException):
    pass
