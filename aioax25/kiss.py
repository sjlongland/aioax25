#!/usr/bin/env python3

"""
KISS serial interface handler.  This allows basic support for talking to
KISS-based TNCs, managing the byte stuffing/unstuffing.
"""

from enum import Enum
from asyncio import get_event_loop
from serial import Serial, EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from .signal import Signal
from binascii import b2a_hex
import time
import logging
import socket


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
                if last == BYTE_FESC:
                    yield last
                else:
                    last = BYTE_FESC
            elif last == BYTE_FESC:
                if byte == BYTE_TFEND:
                    yield BYTE_FEND
                elif byte == BYTE_TFESC:
                    yield BYTE_FESC
                else:
                    yield last
                    yield byte
                last = None
            else:
                yield byte

    @classmethod
    def decode(cls, frame):
        """
        Decode a raw KISS frame.
        """
        frame = bytearray(cls._unstuff_bytes(frame))
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
        return bytes(self._stuff_bytes(out))

    def __str__(self):
        return '%s{Port %d, Cmd 0x%02x, Payload %s}' % (
                self.__class__.__name__,
                self.port,
                self.cmd,
                b2a_hex(self.payload).decode()
        )

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
KISSCommand._register(CMD_RETURN, KISSCmdReturn)


class KISSCmdData(KISSCommand):
    def __init__(self, port, payload, cmd=CMD_DATA):
        assert cmd == CMD_DATA
        super(KISSCmdData, self).__init__(port=port,
                cmd=CMD_DATA, payload=payload)
KISSCommand._register(CMD_DATA, KISSCmdData)


# KISS device interface


class BaseKISSDevice(object):
    """
    Base class for a KISS device.  This may have between 1 and 16 KISS
    ports hanging off it.
    """
    def __init__(self, reset_on_close=True,
            send_block_size=128, send_block_delay=0.1,
            kiss_commands=['INT KISS', 'RESET'],
            prompt='cmd:', log=None, loop=None):
        if log is None:
            log = logging.getLogger(self.__class__.__module__)
        if loop is None:
            loop = get_event_loop()
        self._log = log
        self._protocol = None
        self._rx_buffer = bytearray()
        self._tx_buffer = bytearray()
        self._loop = loop
        self._port = {}
        self._state = KISSDeviceState.CLOSED
        self._open_time = 0
        self._reset_on_close = reset_on_close
        self._kiss_commands = kiss_commands
        self._kiss_rem_commands = None
        self._frame_seen = False
        self._send_block_size = send_block_size
        self._send_block_delay = send_block_delay

    def _receive(self, data):
        """
        Handle incoming data by appending to our receive buffer.  The
        data given may contain partial frames.
        """
        if self._log.isEnabledFor(logging.DEBUG):
            self._log.debug('RECV RAW %r', b2a_hex(data).decode())

        self._rx_buffer += data
        if self._state == KISSDeviceState.OPENING:
            self._loop.call_soon(self._check_open)
        else:
            self._loop.call_soon(self._receive_frame)

    def _send(self, frame):
        """
        Send a frame via the underlying transport.
        """
        rawframe = bytes(frame)

        if self._log.isEnabledFor(logging.DEBUG):
            self._log.debug('XMIT FRAME %r', b2a_hex(rawframe).decode())

        if not self._tx_buffer.endswith(bytearray([BYTE_FEND])):
            self._tx_buffer += bytearray([BYTE_FEND])

        self._tx_buffer += bytes(rawframe) \
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
            self._rx_buffer = bytearray()
            return

        self._log.debug('RECV FRAME start at %d', start)

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

        self._log.debug('RECV FRAME end at %d', end)

        # Everything between those points is our frame.
        frame = self._rx_buffer[1:end]
        self._rx_buffer = self._rx_buffer[end:]

        if self._log.isEnabledFor(logging.DEBUG):
            self._log.debug('RECEIVED FRAME %s, REMAINING %s',
                    b2a_hex(frame).decode(),
                    b2a_hex(self._rx_buffer).decode()
            )

        # Two consecutive FEND bytes are valid, ignore these "empty" frames
        if len(frame) > 0:
            # Decode the frame
            self._loop.call_soon(self._dispatch_rx_frame,
                    KISSCommand.decode(frame))

        # If we just have a FEND, stop here.
        if bytes(self._rx_buffer) == bytearray([BYTE_FEND]):
            return

        # If there is more to send, call ourselves via the IO loop
        if len(self._rx_buffer):
            self._loop.call_soon(self._receive_frame)

    def _dispatch_rx_frame(self, frame):
        """
        Pass a frame to the underlying interface.
        """
        try:
            port = self._port[frame.port]
        except KeyError:
            # Port not defined.
            self._log.debug('RECV FRAME dropped %s', frame)
            return

        # Dispatch this frame to the port.  Swallow exceptions so we
        # don't choke the IO loop.
        self._log.debug('RECV FRAME dispatch %s', frame)
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
        data = self._tx_buffer[:self._send_block_size]
        self._tx_buffer = self._tx_buffer[self._send_block_size:]

        if self._log.isEnabledFor(logging.DEBUG):
            self._log.debug('XMIT RAW %r', b2a_hex(data).decode())

        self._send_raw_data(data)

        # If we are closing, wait for this to be sent
        if (self._state == KISSDeviceState.CLOSING) and \
                (len(self._tx_buffer) == 0):
            self._close()
            return

        if self._tx_buffer:
            self._loop.call_later(self._send_block_delay, self._send_data)

    def _init_kiss(self):
        assert self.state == KISSDeviceState.OPENING, \
                'Device is not opening'

        self._kiss_rem_commands = self._kiss_commands.copy()
        self._send_kiss_cmd()

    def _send_kiss_cmd(self):
        try:
            command = self._kiss_rem_commands.pop(0)
        except IndexError:
            # Should be open now.
            self._open_time = time.time()
            self._state = KISSDeviceState.OPEN
            self._rx_buffer = bytearray()
            return

        self._log.debug('Sending %r', command)
        command = command.encode('US-ASCII')
        self._rx_buffer = bytearray()
        for bv in command:
            self._send_raw_data(bytes([bv]))
            time.sleep(0.1)
        self._send_raw_data(b'\r')
        self._loop.call_later(0.5, self._check_open)

    def _check_open(self):
        """
        Handle opening of the port
        """
        self._loop.call_soon(self._send_kiss_cmd)

    def __getitem__(self, port):
        """
        Retrieve an instance of a specified port.
        """
        try:
            return self._port[port]
        except KeyError:
            pass

        self._log.debug('OPEN new port %d', port)
        p = KISSPort(self, port, log=self._log.getChild('port%d' % port))
        self._port[port] = p
        return p

    @property
    def state(self):
        return self._state

    def open(self):
        assert self.state == KISSDeviceState.CLOSED, \
                'Device is not closed'
        self._log.debug('Opening device')
        self._state = KISSDeviceState.OPENING
        self._open()

    def close(self):
        assert self.state == KISSDeviceState.OPEN, \
                'Device is not open'
        self._log.debug('Closing device')
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
        self._loop.add_reader(self._serial.fileno(), self._on_recv_ready)
        self._loop.call_soon(self._init_kiss)

    def _close(self):
        # Remove handlers
        self._loop.remove_reader(self._serial.fileno())

        # Wait for all data to be sent.
        self._serial.flush()

        # Close the port
        self._serial.close()
        self._serial = None
        self._state = KISSDeviceState.CLOSED

    def _on_recv_ready(self):
        try:
            self._receive(self._serial.read(self._serial.in_waiting))
        except:
            self._log.exception('Failed to read from serial device')

    def _send_raw_data(self, data):
        self._serial.write(data)


class TCPKISSDevice(BaseKISSDevice):

    _interface = None
    READ_BYTES = 1000

    def __init__(self, host: str, port: int, *args, **kwargs):
        super(TCPKISSDevice, self).__init__(*args, **kwargs)
        self.address = (host, port)

    def _open(self):
        self._interface = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._interface.connect(self.address)
        self._loop.add_reader(self._interface, self._on_recv_ready)
        self._loop.call_soon(self._init_kiss)

    def _on_recv_ready(self):
        try:
            read_data = self._interface.recv(self.READ_BYTES)
            self._receive(read_data)
        except:
            self._log.exception('Failed to read from socket device')

    def _send_raw_data(self, data):
        self._interface.send(data)

    def _close(self):
        self._loop.remove_reader(self._interface)
        self._interface.close()
        self._interface = None
        self._state = KISSDeviceState.CLOSED


# Port interface


class KISSPort(object):
    """
    A KISS port represents a port interface on a KISS device.  There can be
    a maximum of 16 ports per device, identified by a 4-bit integer.
    """
    def __init__(self, device, port, log):
        """
        Create a new port attached to the given device.
        """
        self._device = device
        self._port = port
        self._log = log

        # Signal for receiving packets
        self.received = Signal()

    @property
    def port(self):
        return self._port

    def send(self, frame):
        """
        Send a raw AX.25 frame to the TNC via this port.
        """
        self._log.debug('XMIT AX.25 %s', frame)
        self._device._send(KISSCmdData(self.port, bytes(frame)))

    def _receive_frame(self, frame):
        """
        Receive and emit an incoming frame from the port.
        """
        self._log.debug('Received frame %s', frame)

        if not isinstance(frame, KISSCmdData):
            # TNC is not supposed to send this!
            return

        self.received.emit(frame=frame.payload)
