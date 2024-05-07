#!/usr/bin/env python3

import asyncio
import argparse
import logging

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
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


class AX25Call(object):
    def __init__(self, source, destination, kissparams, port=0):
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
        self._peer = self._station.getpeer(destination)
        self._peer.received_information.connect(self._on_receive)

    def _on_receive(self, frame, **kwargs):
        with patch_stdout():
            if frame.pid == 0xF0:
                # No L3 protocol
                print("\n".join(frame.payload.decode().split("\r")))
            else:
                print("[PID=0x%02x] %r" % (frame.pid, frame.payload))

    async def interact(self):
        # Open the KISS interface
        self._device.open()

        # TODO: implement async functions on KISS device to avoid this!
        while self._device.state != KISSDeviceState.OPEN:
            await asyncio.sleep(0.1)

        # Connect to the remote station
        future = asyncio.Future()

        def _state_change_fn(state, **kwa):
            if state is AX25PeerState.CONNECTED:
                future.set_result(None)
            elif state is AX25PeerState.DISCONNECTED:
                future.set_exception(IOError("Connection refused"))

        self._peer.connect_state_changed.connect(_state_change_fn)
        self._peer.connect()
        await future
        self._peer.connect_state_changed.disconnect(_state_change_fn)

        # We should now be connected
        self._log.info("CONNECTED to %s", self._peer.address)
        finished = False
        session = PromptSession()
        while not finished:
            if self._peer.state is not AX25PeerState.CONNECTED:
                finished = True

            with patch_stdout():
                # Prompt for user input
                txinput = await session.prompt_async(
                    "%s>" % self._peer.address
                )
            if txinput:
                self._peer.send(("%s\r" % txinput).encode())

        if self._peer.state is not AX25PeerState.DISCONNECTED:
            self._log.info("DISCONNECTING")
            future = asyncio.Future()

            def _state_change_fn(state, **kwa):
                if state is AX25PeerState.DISCONNECTED:
                    future.set_result(None)

            self._peer.connect_state_changed.connect(_state_change_fn)
            self._peer.disconnect()
            await future
            self._peer.connect_state_changed.disconnect(_state_change_fn)

        self._log.info("Finished")


async def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--log-level", default="info", type=str, help="Log level")
    ap.add_argument("--port", default=0, type=int, help="KISS port number")
    ap.add_argument(
        "config", type=str, help="KISS serial port configuration file"
    )
    ap.add_argument("source", type=str, help="Source callsign/SSID")
    ap.add_argument("destination", type=str, help="Source callsign/SSID")

    args = ap.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format=(
            "%(asctime)s %(name)s[%(filename)s:%(lineno)4d] "
            "%(levelname)s %(message)s"
        ),
    )
    config = safe_load(open(args.config, "r").read())

    ax25call = AX25Call(args.source, args.destination, config, args.port)
    await ax25call.interact()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
