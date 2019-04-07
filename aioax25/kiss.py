#!/usr/bin/env python3

"""
KISS serial interface handler.  This allows basic support for talking to
KISS-based TNCs, managing the byte stuffing/unstuffing.
"""

from enum import Enum
from asyncio import Protocol, get_event_loop
from serial import Serial, EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from weakref import WeakValueDictionary
from .signal import Signal
import logging


# Constants


BYTE_FEND   = 0xc0
BYTE_FESC   = 0xdb
BYTE_TFEND  = 0xdc
BYTE_TFESC  = 0xdd

CMD_DATA    = 0x00
CMD_TXDELAY = 0x01
CMD_P       = 0x02
CMD_SLOTTIME= 0x03
CMD_TXTAIL  = 0x04
CMD_FDUPLEX = 0x05
CMD_SETHW   = 0x06
CMD_RETURN  = 0x0f


# States


class KISSDeviceState(Enum):
    """
    States permitted by a KISS device:
    - CLOSED: Serial port is closed
    - INIT: Serial port just opened, TNC may be in TNC2-mode and
            the library is attempting to put it into KISS mode.
    - OPEN: Serial port is open, TNC in KISS mode.
    - CLOSING: Close instruction just received.  Putting TNC back into
      TNC2-mode if requested then closing the port.
    """
    CLOSED = 0
    OPENING = 1
    OPEN = 2
    CLOSING = 3


# Command classes


class KISSCommand(object):
    """
    KISS base command class
    """

    # Known commands: this will be populated later.
    _KNOWN_COMMANDS = {}

    @classmethod
    def _register(cls, cmd, subclass):
        assert cmd not in cls._KNOWN_COMMANDS
        cls._KNOWN_COMMANDS[cmd] = subclass

    @classmethod
    def _stuff_bytes(cls, data):
        """
        Byte-stuff incoming byte string.
        """
        for byte in data:
            if byte == BYTE_FEND:
                yield BYTE_FESC
                yield BYTE_TFEND
            elif byte == BYTE_FESC:
                yield BYTE_FESC
                yield BYTE_TFESC
            else:
                yield byte

    @classmethod
    def _unstuff_bytes(cls, data):
        """
        Un-byte-stuff incoming byte string.
        """
        last = None
        for byte in data:
            if byte == BYTE_FESC:
                last = BYTE_FESC
            elif last == BYTE_FESC:
                if byte == BYTE_TFEND:
                    yield BYTE_FEND
                elif byte == BYTE_TFESC:
                    yield BYTE_FESC
                else:
                    yield last
                    yield byte
            else:
                yield byte

    @classmethod
    def decode(cls, frame):
        """
        Decode a raw KISS frame.
        """
        frame = cls._unstuff_bytes(frame)
        port = frame[0] >> 4
        cmd  = frame[0] & 0x0f
        subclass = cls._KNOWN_COMMANDS.get(cmd, cls)
        return subclass(port=port, cmd=cmd, payload=frame[1:])

    def __init__(self, port, cmd, payload=None):
        self._port = port
        self._cmd = cmd
        self._payload = payload

    def __bytes__(self):
        out = bytearray([
            ((self._port & 0x0f) << 4) | (self._cmd & 0x0f)
        ])
        if self._payload:
            out += self._payload

        # Encode the byte sequences
        return bytearray(self._stuff_bytes(out))

    @property
    def port(self):
        return self._port

    @property
    def cmd(self):
        return self._cmd

    @property
    def payload(self):
        return self._payload


class KISSCmdReturn(KISSCommand):
    """
    Emit a return command to the TNC.
    """
    def __init__(self):
        super(KISSCmdReturn, self).__init__(port=15, cmd=CMD_RETURN)


class KISSCmdData(KISSCommand):
    def __init__(self, port, payload):
        super(KISSCmdData, self).__init__(port=port,
                cmd=CMD_DATA, payload=payload)


# KISS device interface


class BaseKISSDevice(object):
    """
    Base class for a KISS device.  This may have between 1 and 16 KISS
    ports hanging off it.
    """
    def __init__(self, reset_on_close=True, loop=None):
        if loop is None:
            loop = get_event_loop()
        self._protocol = None
        self._rx_buffer = bytearray()
        self._tx_buffer = bytearray()
        self._loop = loop
        self._port = WeakValueDictionary()
        self._state = KISSDeviceState.CLOSED
        self._reset_on_close = True

    def _receive(self, data):
        """
        Handle incoming data by appending to our receive buffer.  The
        data given may contain partial frames.
        """
        self._rx_buffer += data
        self._loop.call_soon(self._receive_frame)

    def _send(self, rawframe):
        """
        Send a frame via the underlying transport.
        """
        if not self._tx_buffer.endswith(bytearray([BYTE_FEND])):
            self._tx_buffer += bytearray([BYTE_FEND])

        self._tx_buffer += bytes(rawframe)
                         + bytearray([BYTE_FEND])
        self._loop.call_soon(self._send_data)

    def _receive_frame(self):
        """
        Scan the receive buffer for incoming frames and send these to the
        underlying device.  If more than one frame is present, schedule
        ourselves again with the IO loop.
        """
        # Locate the first FEND byte
        try:
            start = self._rx_buffer.index(BYTE_FEND)
        except ValueError:
            # No frames waiting
            return

        # Discard the proceeding junk
        self._rx_buffer = self._rx_buffer[start:]
        del start
        assert self._rx_buffer[0] == BYTE_FEND

        # Locate the last FEND byte of the frame
        try:
            end = self._rx_buffer.index(BYTE_FEND, 1)
        except ValueError:
            # Uhh huh, so frame is incomplete.
            return

        # Everything between those points is our frame.
        frame = self._rx_buffer[1:end]
        self._rx_buffer = self._rx_buffer[end:]

        # Two consecutive FEND bytes are valid, ignore these "empty" frames
        if len(frame) > 0:
            # Decode the frame
            self._loop.call_soon(self._dispatch_rx_frame,
                    KISSCommand.decode(frame))

        # If there is more to send, call ourselves via the IO loop
        if len(self._rx_buffer):
            self._loop.call_soon(self._receive_frame)

    def _dispatch_rx_frame(self, frame):
        """
        Pass a frame to the underlying interface.
        """
        try:
            # First byte contains the port number and command.
            # Port number is the high 4 bits.
            port = self._port[frame[0] >> 4]
        except KeyError:
            # Port not defined.
            return

        # Dispatch this frame to the port.  Swallow exceptions so we
        # don't choke the IO loop.
        try:
            port._receive_frame(frame)
        except:
            logging.getLogger(self.__class__.__module__).exception(
                    'Port %s failed to handle frame %s',
                    port, frame
            )

    def _send_data(self):
        """
        Send the next block of data waiting in the buffer.
        """
        data = self._tx_buffer
        self._tx_buffer = bytearray()
        self._send_raw_data(data)

        # If we are closing, wait for this to be sent
        if self._state == KISSDeviceState.CLOSING:
            self._close()

    def _init_kiss(self):
        assert self.state == KISSDeviceState.OPENING, \
                'Device is not opening'
        # For now, just blindly send a INT KISS command followed by a RESET.
        self._send_raw_data('\rINT KISS\rRESET\r')
        self._state = KISSDeviceState.OPEN

    def __getitem__(self, port):
        """
        Retrieve an instance of a specified port.
        """
        try:
            return self._port[port]
        except KeyError:
            pass

        p = KISSPort(self, port)
        self._port[port] = p
        return p

    @property
    def state(self):
        return self._state

    def open(self):
        assert self.state == KISSDeviceState.CLOSED, \
                'Device is not closed'
        self._state = KISSDeviceState.OPENING
        self._open()

    def close(self):
        assert self.state == KISSDeviceState.OPEN, \
                'Device is not open'
        self._state = KISSDeviceState.CLOSING
        if self._reset_on_close:
            self._send(KISSCmdReturn())
        else:
            self._close()


class SerialKISSDevice(BaseKISSDevice):
    def __init__(self, device, baudrate, *args, **kwargs):
        super(SerialKISSDevice, self).__init__(*args, **kwargs)
        self._serial = None
        self._device = device
        self._baudrate = baudrate

    def _open(self):
        self._serial = Serial(port=self._device, baudrate=self._baudrate,
                bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE,
                timeout=None, xonxoff=False, rtscts=False, write_timeout=None,
                dsrdtr=False, inter_byte_timeout=None)
        self._serial.open()
        self._loop.add_reader(self._serial.fileno(), self._on_recv_ready)
        self._loop.add_writer(self._serial.fileno(), self._on_xmit_ready)
        self._loop.call_soon(self._init_kiss)

    def _close(self):
        # Remove handlers
        self._loop.remove_reader(self._serial.fileno())
        self._loop.remove_writer(self._serial.fileno())

        # Wait for all data to be sent.
        self._serial.flush()

        # Close the port
        self._serial.close()
        self._serial = None
        self._state = KISSDeviceState.CLOSED


# Port interface


class KISSPort(object):
    """
    A KISS port represents a port interface on a KISS device.  There can be
    a maximum of 16 ports per device, identified by a 4-bit integer.
    """
    def __init__(self, device, port):
        """
        Create a new port attached to the given device.
        """
        self._device = device
        self._port = port

        # Signal for receiving packets
        self.received = Signal()

    def send(self, frame):
        """
        Send a raw AX.25 frame to the TNC via this port.
        """
        self._device._send(KISSCmdData(self._port, bytes(frame)))

    def _receive_frame(self, frame):
        """
        Receive and emit an incoming frame from the port.
        """
        if not isinstance(frame, KISSCmdData):
            # TNC is not supposed to send this!
            return

        self.received.emit(frame=frame)
