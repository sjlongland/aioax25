#!/usr/bin/env python3

"""
KISS serial interface handler.  This allows basic support for talking to
KISS-based TNCs, managing the byte stuffing/unstuffing.
"""

from enum import Enum
from asyncio import Protocol, ensure_future, get_event_loop
from serial_asyncio import create_serial_connection
from serial import EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from .signal import Signal
from binascii import b2a_hex
import time
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
            log=None, loop=None, **kwargs):
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


class BaseTransportDevice(BaseKISSDevice):
    def __init__(self, *args, **kwargs):
        super(BaseTransportDevice, self).__init__(*args, **kwargs)
        self._transport = None

    def _make_protocol(self):
        """
        Return a Protocol instance that will handle the KISS traffic for the
        asyncio transport.
        """
        return KISSProtocol(
            self._on_connect,
            self._receive,
            self._on_close,
            self._log.getChild('protocol')
        )

    async def _open_connection(self): # pragma: no cover
        """
        Open a connection to the underlying transport.
        """
        raise NotImplementedError('Abstract function')

    def _open(self):
        ensure_future(self._open_connection())

    def _on_connect(self, transport):
        self._transport = transport
        self._init_kiss()

    def _close(self):
        # Wait for all data to be sent.
        self._transport.flush()

        # Close the port
        self._transport.close()

        # Clean up
        self._on_close()

    def _on_close(self, exc=None):
        if exc is not None:
            self._log.error('Closing port due to error %r', exc)

        self._transport = None
        self._state = KISSDeviceState.CLOSED

    def _send_raw_data(self, data):
        self._transport.write(data)


class SerialKISSDevice(BaseTransportDevice):
    """
    A KISS device attached to a serial port.  The serial port may be a
    pseudo-TTY, USB-connected serial port or platform-attached serial port.
    The ``baudrate`` parameter specifies the baud rate used to communicate
    with the TNC, not the speed of the AX.25 network which may be a different
    speed.

    The serial port link is assumed to use 8-bit wide frames, no parity bits
    and one stop bit with no flow control.

    :param device: Device node name to connect to (e.g. `/dev/ttyS0`, `COM3:`)
    :type device: ``str``
    :param baudrate: Baud rate to connect to the serial port at.
    :type baudrate: ``int``
    :Keyword Arguments: These are passed (via ``BaseTransportDevice``) through
                        to ``BaseKISSDevice`` unchanged.
    """
    def __init__(self, device, baudrate, *args, **kwargs):
        super(SerialKISSDevice, self).__init__(*args, **kwargs)
        self._device = device
        self._baudrate = baudrate

    async def _open_connection(self):
        await create_serial_connection(
                self._loop,
                self._make_protocol,
                self._device,
                baudrate=self._baudrate,
                bytesize=EIGHTBITS,
                parity=PARITY_NONE,
                stopbits=STOPBITS_ONE,
                timeout=None, xonxoff=False,
                rtscts=False, write_timeout=None,
                dsrdtr=False, inter_byte_timeout=None
        )


class TCPKISSDevice(BaseTransportDevice):
    """
    A KISS device exposed via a TCP serial server.  This may be a real TNC
    attached to a serial-to-Ethernet gateway, or a soft-TNC.

    :param host: Host name or IP address of the remote TCP server.
    :type device: ``str``
    :param port: Port number on the remote TCP server where the KISS TNC is
                 listening.
    :type port: ``int``
    :param ssl: Whether or not to use Transport Layer Security to connect to
                the remote TCP server.
    :type ssl: ``None``, ``ssl.SSLContext`` or ``True``
    :param family: Socket address family to use when connecting, e.g.
                   ``socket.AF_INET`` for IPv4, ``socket.AF_INET6`` for IPv6,
                   or ``0`` for any.
    :type family: ``int``
    :param proto: Specifies the address protocol.  Exposed for completeness.
                  See the ``socket`` module for further details.
    :type proto: ``int``
    :param flags: Specifies special socket flags used for the connection.  See
                  the ``socket`` module for possible flags.
    :type flags: ``int``
    :param sock: Specifies an optional existing socket object to use for the
                 connection.
    :type sock: ``None`` or ``socket.socket``
    :param local_addr: Local interface address to bind to when connecting.
    :type local_addr: ``None`` or ``str``
    :param server_hostname: Remote server name if needed for Server Name
                            Identification.  In most cases, ``host`` should
                            be a host name and this argument will not be
                            required.  Not used if TLS is disabled.
    :type server_hostname: ``None`` or ``str``
    :Keyword Arguments: These are passed (via ``BaseTransportDevice``) through
                        to ``BaseKISSDevice`` unchanged.
    """
    def __init__(self, host, port, *args, ssl=None, family=0, proto=0, flags=0,
            sock=None, local_addr=None, server_hostname=None, **kwargs):
        super(TCPKISSDevice, self).__init__(*args, **kwargs)

        # Bundle up all the connection arguments together.
        self._conn_args = dict(
                host=host, port=port, ssl=ssl, family=family,
                proto=proto, flags=flags, sock=sock, local_addr=local_addr,
                server_hostname=server_hostname
        )

    async def _open_connection(self):
        await self._loop.create_connection(
                self._make_protocol,
                **self._conn_args
        )


class SubprocKISSDevice(BaseTransportDevice):
    """
    A KISS device that calls a subprocess to communicate with the KISS TNC.
    The subprocess is assumed to accept KISS data on ``stdin`` and emit KISS
    data on ``stdout``.  ``stderr`` traffic is logged but otherwise ignored.

    :param command: Specifies the subprocess command to execute along with any
                    arguments.
    :type command: ``list[str]``
    :param shell: Use a shell to execute the command given.  The command will
                  be concatenated together with spaces to form a single
                  string.  By default, this is ``False``.
    :type shell: ``bool``
    :Keyword Arguments: These are passed (via ``BaseTransportDevice``) through
                        to ``BaseKISSDevice`` unchanged.
    """
    def __init__(self, command, *args, shell=False, **kwargs):
        super(SubprocKISSDevice, self).__init__(*args, **kwargs)
        self._command = command
        self._shell = shell

    def _make_protocol(self):
        """
        Return a SubprocessProtocol instance that will handle the KISS traffic for the
        asyncio transport.
        """
        return KISSSubprocessProtocol(
            self._on_connect,
            self._receive,
            self._on_close,
            self._log.getChild('protocol')
        )

    async def _open_connection(self):
        if self._shell:
            await self._loop.subprocess_shell(
                    self._make_protocol,
                    ' '.join(self._command)
            )
        else:
            await self._loop.subprocess_exec(
                    self._make_protocol,
                    *self._command
            )

    def _send_raw_data(self, data):
        transport = self._transport.get_pipe_transport(0).write(data)


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


# Protocol interface adaptors for asyncio


class KISSProtocol(Protocol):
    """
    KISSProtocol basically is a wrapper around asyncio's "Protocol"
    structure.
    """
    def __init__(self, on_connect, on_receive, on_close, log):
        super(KISSProtocol, self).__init__()

        self._on_connect = on_connect
        self._on_receive = on_receive
        self._on_close = on_close
        self._log = log

    def connection_made(self, transport):
        try:
            self._on_connect(transport)
        except:
            self._log.exception('Failed to handle connection establishment')
            transport.close()

    def data_received(self, data):
        try:
            self._on_receive(data)
        except:
            self._log.exception('Failed to handle incoming data')

    def connection_lost(self, exc):
        try:
            self._on_close(exc)
        except:
            self._log.exception('Failed to handle connection loss')


class KISSSubprocessProtocol(Protocol):
    """
    KISSSubprocessProtocol is nearly identical to KISSProtocol but wraps
    SubprocessProtocol instead.
    """
    def __init__(self, on_connect, on_receive, on_close, log):
        super(KISSSubprocessProtocol, self).__init__()

        self._on_connect = on_connect
        self._on_receive = on_receive
        self._on_close = on_close
        self._log = log

    def connection_made(self, transport):
        try:
            self._on_connect(transport)
        except:
            self._log.exception('Failed to handle connection establishment')
            transport.close()

    def pipe_data_received(self, fd, data):
        try:
            if fd == 1: # stdout
                self._on_receive(data)
            else:
                self._log.debug('Data received on fd=%d: %r', fd, data)
        except:
            self._log.exception(
                    'Failed to handle incoming data %r on fd=%d', data, fd
            )

    def process_exited(self):
        try:
            self._on_close(None)
        except:
            self._log.exception('Failed to handle process exit')


# KISS device factory

def make_device(type, **kwargs):
    """
    Create a KISS device of the specified type.  This is a convenience for
    applications that load their configuration via a `dict`-like configuration
    file format such as JSON, YAML or TOML.

    :param type: Type of KISS device to make (see below)
    :type type: ``str``
    :Keyword Arguments: These will be passed to the relevant device class
                        as-is.  Some common arguments for all class types:
      * ``reset_on_close`` (``bool`` = ``True``): Whether or not a "return
        from KISS" command (``C0 FF C0``) should be sent to the TNC on
        closing.
      * ``send_block_size`` (``int`` = ``128``): The number of bytes to send
        in a single write request at a time.  Some KISS TNCs have very small
        serial buffers, and so this, along with ``send_block_delay``, allow
        the outgoing traffic to be "dribbled out" at a rate that avoids
        overflow issues.
      * ``send_block_delay`` (``float`` = ``0.1``): The time to wait between
        consecutive blocks so that the TNC can "catch up".
      * ``kiss_commands`` (``list[str]`` = ``["INT KISS", "RESET"]``):
        The TNC-2 commands to transmit to the TNC after opening to put the
        TNC into KISS mode.  The default value suits Kantronics KPC3 TNCs.
      * ``log`` (``logging.Logger``): A logger interface to log debugging
        traffic.  If not supplied, a default one is created.
      * ``loop`` (``asyncio.AbstractEventLoop``): Asynchronous I/O event loop
        that will schedule the operations for the KISS device.  By default,
        the current event loop (``asyncio.get_event_loop()``) is used.

    +----------------+-------------------------------------------------+
    | ``type`` value | Device type and required arguments              |
    +----------------+-------------------------------------------------+
    | ``serial``     | Serial port KISS device (``SerialKISSDevice``). |
    |                | * ``device`` (``str``):                         |
    |                |   Device name, e.g. `/dev/ttyS0`, `COM3:`       |
    |                | * ``baudrate`` (``int``):                       |
    |                |   Serial port baud rate, e.g. 9600 baud         |
    +----------------+-------------------------------------------------+
    | ``subproc``    | Sub-process KISS device (``SubprocKISSDevice``).|
    |                | * ``command`` (``list[str]``):                  |
    |                |   Command and arguments to execute.             |
    |                | * ``shell`` (``bool``):                         |
    |                |   If set to ``True``, run in a sub-shell.       |
    +----------------+-------------------------------------------------+
    | ``tcp``        | TCP KISS device (``TCPKISSDevice``).            |
    |                | * ``host`` (``str``):                           |
    |                |   IP address or host name of the remote host.   |
    |                | * ``port`` (``int``):                           |
    |                |   TCP port number for the KISS interface.       |
    +----------------+-------------------------------------------------+
    """

    if type == 'serial':
        return SerialKISSDevice(**kwargs)
    elif type == 'subproc':
        return SubprocKISSDevice(**kwargs)
    elif type == 'tcp':
        return TCPKISSDevice(**kwargs)
    else:
        raise ValueError('Unrecognised type=%r' % (type,))
