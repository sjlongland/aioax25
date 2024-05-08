#!/usr/bin/env python3

"""
Very crude program for listening for an AX.25 connection, then launching a
program for the remote caller to interact with.  e.g. to make a Python
interpreter available over the packet network (and open a remote code
execution hole in the process!), use something like:

```
$ python3 -m aioax25.tools.listen kiss-config.yml N0CALL-12 -- python -i
```

"""

import asyncio
from asyncio import subprocess
import argparse
import logging

from yaml import safe_load

# aioax25 imports
# from aioax25.kiss import …
# from aioax25.interface import …
# etc… if you're copying this for your own code
from ..kiss import make_device, KISSDeviceState
from ..interface import AX25Interface
from ..station import AX25Station
from ..peer import AX25PeerState
from ..version import AX25Version


class SubprocProtocol(asyncio.Protocol):
    """
    SubprocProtocol manages the link to the sub-process on behalf of the peer
    session.
    """

    def __init__(self, on_connect, on_receive, on_close, log):
        super(SubprocProtocol, self).__init__()

        self._on_connect = on_connect
        self._on_receive = on_receive
        self._on_close = on_close
        self._log = log

    def connection_made(self, transport):
        try:
            self._log.debug("Announcing connection: %r", transport)
            self._on_connect(transport)
        except Exception as e:
            self._log.exception("Failed to handle connection establishment")
            transport.close()
            self._on_connect(None)

    def pipe_data_received(self, fd, data):
        try:
            if fd == 1:  # stdout
                self._on_receive(data)
            else:
                self._log.debug("Data received on fd=%d: %r", fd, data)
        except:
            self._log.exception(
                "Failed to handle incoming data %r on fd=%d", data, fd
            )

    def pipe_connection_lost(self, fd, exc):
        self._log.debug("FD %d closed (exc=%s)", fd, exc)
        try:
            self._on_close(exc)
        except:
            self._log.exception("Failed to handle process pipe close")

    def process_exited(self):
        try:
            self._on_close(None)
        except:
            self._log.exception("Failed to handle process exit")


class PeerSession(object):
    def __init__(self, peer, command, echo, log):
        self._peer = peer
        self._log = log
        self._command = command
        self._cmd_transport = None
        self._echo = echo

        peer.received_information.connect(self._on_peer_received)
        peer.connect_state_changed.connect(self._on_peer_state_change)

    async def init(self):
        self._log.info("Launching sub-process")
        await asyncio.get_event_loop().subprocess_exec(
            self._make_protocol, *self._command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, bufsize=0
        )

    def _make_protocol(self):
        """
        Return a SubprocessProtocol instance that will handle the KISS traffic for the
        asyncio transport.
        """

        def _on_connect(transport):
            self._log.info("Sub-process transport now open")
            self._cmd_transport = transport

        return SubprocProtocol(
            _on_connect,
            self._on_subproc_received,
            self._on_subproc_closed,
            self._log.getChild("protocol"),
        )

    def _on_subproc_received(self, data):
        """
        Pass data from the sub-process to the AX.25 peer.
        """
        self._log.debug("Received from subprocess: %r", data)
        if self._peer.state is AX25PeerState.CONNECTED:
            # Peer still connected, pass to the peer, translating newline with
            # CR as per AX.25 conventions.
            data = b"\r".join(data.split(b"\n"))
            self._log.debug("Writing to peer: %r", data)
            self._peer.send(data)
        elif self._peer.state is AX25PeerState.DISCONNECTED:
            # Peer is not connected, close the subprocess.
            self._log.info("Peer no longer connected, shutting down")
            self._cmd_transport.close()

    def _on_subproc_closed(self, exc=None):
        if exc is not None:
            self._log.error("Closing port due to error %r", exc)

        self._log.info("Sub-process has exited")
        self._cmd_transport = None
        if self._peer.state is not AX25PeerState.DISCONNECTED:
            self._log.info("Closing peer connection")
            self._peer.disconnect()

    def _on_peer_received(self, payload, **kwargs):
        """
        Pass data from the AX.25 peer to the sub-process.
        """
        self._log.debug("Received from peer: %r", payload)
        if self._echo:
            # Echo back to peer
            self._peer.send(payload)

        if self._cmd_transport:
            payload = b"\n".join(payload.split(b"\r"))
            self._log.debug("Writing to subprocess: %r", payload)
            self._cmd_transport.get_pipe_transport(0).write(payload)
        else:
            # Subprocess no longer running, so shut it down.
            self._log.info("Sub-process no longer running, disconnecting")
            self._peer.disconnect()

    def _on_peer_state_change(self, state, **kwargs):
        """
        Handle peer connection state change.
        """
        if state is AX25PeerState.DISCONNECTED:
            self._log.info("Peer has disconnected")
            if self._cmd_transport:
                self._cmd_transport.close()


class AX25Listen(object):
    def __init__(self, source, command, kissparams, port=0, echo=False):
        log = logging.getLogger(self.__class__.__name__)
        kisslog = log.getChild("kiss")
        kisslog.setLevel(logging.INFO)  # KISS logs are verbose!
        intflog = log.getChild("interface")
        intflog.setLevel(logging.INFO)  # interface logs are verbose too!
        stnlog = log.getChild("station")

        self._log = log
        self._device = make_device(**kissparams, log=kisslog)
        self._interface = AX25Interface(self._device[port], log=intflog)
        self._station = AX25Station(
            self._interface,
            source,
            log=stnlog,
        )
        self._station.attach()
        self._command = command
        self._station.connection_request.connect(self._on_connection_request)
        self._echo = echo

    async def listen(self):
        # Open the KISS interface
        self._device.open()

        # TODO: implement async functions on KISS device to avoid this!
        while self._device.state != KISSDeviceState.OPEN:
            await asyncio.sleep(0.1)

        self._log.info("Listening for connections")
        while True:
            await asyncio.sleep(1)

    def _on_connection_request(self, peer, **kwargs):
        # Bounce to the I/O loop
        asyncio.ensure_future(self._connect_peer(peer))

    async def _connect_peer(self, peer):
        self._log.info("Incoming connection from %s", peer.address)
        try:
            session = PeerSession(peer, self._command, self._echo, self._log.getChild(str(peer.address)))
            await session.init()
        except:
            self._log.exception("Failed to initialise peer connection")
            peer.reject()
            return

        # All good?  Accept the connection.
        peer.accept()


async def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--log-level", default="info", type=str, help="Log level")
    ap.add_argument("--port", default=0, type=int, help="KISS port number")
    ap.add_argument("--echo", default=False, action="store_const", const=True,
                    help="Echo input back to the caller")
    ap.add_argument(
        "config", type=str, help="KISS serial port configuration file"
    )
    ap.add_argument("source", type=str, help="Source callsign/SSID")
    ap.add_argument("command", type=str, nargs="+",
                    help="Program + args to run")

    args = ap.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format=(
            "%(asctime)s %(name)s[%(filename)s:%(lineno)4d] "
            "%(levelname)s %(message)s"
        ),
    )
    config = safe_load(open(args.config, "r").read())

    ax25listen = AX25Listen(args.source, args.command, config, args.port,
                            args.echo)
    await ax25listen.listen()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
