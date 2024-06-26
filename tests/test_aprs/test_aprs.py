#!/usr/bin/env python3

import logging
from functools import partial
from signalslot import Signal

from aioax25.aprs import APRSInterface
from aioax25.frame import AX25UnnumberedInformationFrame, AX25Address
from aioax25.aprs.message import APRSMessageFrame, APRSMessageHandler

from ..loop import DummyLoop


class DummyAX25Interface(object):
    def __init__(self):
        self._loop = DummyLoop()
        self.bind_calls = []
        self.transmitted = []
        self.received_msg = Signal()

    def bind(self, callback, callsign, ssid=0, regex=False):
        self.bind_calls.append((callback, callsign, ssid, regex))

    def transmit(self, frame):
        self.transmitted.append(frame)


class DummyMessageHandler(object):
    def _on_response(self):
        pass


def test_constructor_log():
    """
    Test the constructor can accept a logger instance.
    """
    ax25int = DummyAX25Interface()
    log = logging.getLogger("aprslog")
    aprsint = APRSInterface(ax25int, "VK4MSL-10", log=log)
    assert log is aprsint._log


def test_constructor_bind():
    """
    Test the constructor binds to given destination addresses.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(
        ax25int,
        "VK4MSL-10",
        listen_destinations=[
            dict(callsign="^AIR", regex=True, ssid=None),  # Legacy
            dict(callsign="^ALL", regex=True, ssid=None),
            dict(callsign="^AP", regex=True, ssid=None),
            dict(callsign="BEACON", regex=False, ssid=None),
            dict(callsign="^CQ", regex=True, ssid=None),
            dict(callsign="^GPS", regex=True, ssid=None),
            dict(callsign="^DF", regex=True, ssid=None),
            dict(callsign="^DGPS", regex=True, ssid=None),
            dict(callsign="^DRILL", regex=True, ssid=None),
            dict(callsign="^ID", regex=True, ssid=None),
            dict(callsign="^JAVA", regex=True, ssid=None),
            dict(callsign="^MAIL", regex=True, ssid=None),
            dict(callsign="^MICE", regex=True, ssid=None),
            dict(callsign="^QST", regex=True, ssid=None),
            dict(callsign="^QTH", regex=True, ssid=None),
            dict(callsign="^RTCM", regex=True, ssid=None),
            dict(callsign="^SKY", regex=True, ssid=None),
            dict(callsign="^SPACE", regex=True, ssid=None),
            dict(callsign="^SPC", regex=True, ssid=None),
            dict(callsign="^SYM", regex=True, ssid=None),
            dict(callsign="^TEL", regex=True, ssid=None),
            dict(callsign="^TEST", regex=True, ssid=None),
            dict(callsign="^TLM", regex=True, ssid=None),
            dict(callsign="^WX", regex=True, ssid=None),
            dict(callsign="^ZIP", regex=True, ssid=None),  # Legacy
        ],
    )
    assert aprsint
    assert len(ax25int.bind_calls) == 26

    assert set(
        [
            (call, regex, ssid)
            for (cb, call, ssid, regex) in ax25int.bind_calls
        ]
    ) == set(
        [
            # The first bind call should be for the station SSID
            ("VK4MSL", False, 10),
            # The rest should be the standard APRS ones.
            ("^AIR", True, None),
            ("^ALL", True, None),
            ("^AP", True, None),
            ("BEACON", False, None),
            ("^CQ", True, None),
            ("^GPS", True, None),
            ("^DF", True, None),
            ("^DGPS", True, None),
            ("^DRILL", True, None),
            ("^ID", True, None),
            ("^JAVA", True, None),
            ("^MAIL", True, None),
            ("^MICE", True, None),
            ("^QST", True, None),
            ("^QTH", True, None),
            ("^RTCM", True, None),
            ("^SKY", True, None),
            ("^SPACE", True, None),
            ("^SPC", True, None),
            ("^SYM", True, None),
            ("^TEL", True, None),
            ("^TEST", True, None),
            ("^TLM", True, None),
            ("^WX", True, None),
            ("^ZIP", True, None),
        ]
    )


def test_constructor_bind_destinations_and_altnets():
    """
    Test the constructor binds to both given destinations and alt-nets
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(
        ax25int,
        "VK4MSL-10",
        listen_destinations=[
            dict(callsign="^AIR", regex=True, ssid=None),  # Legacy
            dict(callsign="^ALL", regex=True, ssid=None),
            dict(callsign="^AP", regex=True, ssid=None),
            dict(callsign="BEACON", regex=False, ssid=None),
            dict(callsign="^CQ", regex=True, ssid=None),
            dict(callsign="^GPS", regex=True, ssid=None),
            dict(callsign="^DF", regex=True, ssid=None),
            dict(callsign="^DGPS", regex=True, ssid=None),
            dict(callsign="^DRILL", regex=True, ssid=None),
            dict(callsign="^ID", regex=True, ssid=None),
            dict(callsign="^JAVA", regex=True, ssid=None),
            dict(callsign="^MAIL", regex=True, ssid=None),
            dict(callsign="^MICE", regex=True, ssid=None),
            dict(callsign="^QST", regex=True, ssid=None),
            dict(callsign="^QTH", regex=True, ssid=None),
            dict(callsign="^RTCM", regex=True, ssid=None),
            dict(callsign="^SKY", regex=True, ssid=None),
            dict(callsign="^SPACE", regex=True, ssid=None),
            dict(callsign="^SPC", regex=True, ssid=None),
            dict(callsign="^SYM", regex=True, ssid=None),
            dict(callsign="^TEL", regex=True, ssid=None),
            dict(callsign="^TEST", regex=True, ssid=None),
            dict(callsign="^TLM", regex=True, ssid=None),
            dict(callsign="^WX", regex=True, ssid=None),
            dict(callsign="^ZIP", regex=True, ssid=None),  # Legacy
        ],
        listen_altnets=[dict(callsign="VK4BWI", regex=False, ssid=None)],
    )
    assert aprsint
    assert len(ax25int.bind_calls) == 27

    assert set(
        [
            (call, regex, ssid)
            for (cb, call, ssid, regex) in ax25int.bind_calls
        ]
    ) == set(
        [
            # The first bind call should be for the station SSID
            ("VK4MSL", False, 10),
            # The rest should be the standard APRS ones.
            ("^AIR", True, None),
            ("^ALL", True, None),
            ("^AP", True, None),
            ("BEACON", False, None),
            ("^CQ", True, None),
            ("^GPS", True, None),
            ("^DF", True, None),
            ("^DGPS", True, None),
            ("^DRILL", True, None),
            ("^ID", True, None),
            ("^JAVA", True, None),
            ("^MAIL", True, None),
            ("^MICE", True, None),
            ("^QST", True, None),
            ("^QTH", True, None),
            ("^RTCM", True, None),
            ("^SKY", True, None),
            ("^SPACE", True, None),
            ("^SPC", True, None),
            ("^SYM", True, None),
            ("^TEL", True, None),
            ("^TEST", True, None),
            ("^TLM", True, None),
            ("^WX", True, None),
            ("^ZIP", True, None),
            # Now should be the "alt-nets"
            ("VK4BWI", False, None),
        ]
    )


def test_constructor_bind_altnets():
    """
    Test the constructor binds to "alt-nets" only.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(
        ax25int,
        "VK4MSL-10",
        listen_altnets=[dict(callsign="VK4BWI", regex=False, ssid=None)],
    )
    assert aprsint
    assert len(ax25int.bind_calls) == 2

    assert set(
        [
            (call, regex, ssid)
            for (cb, call, ssid, regex) in ax25int.bind_calls
        ]
    ) == set(
        [
            # The first bind call should be for the station SSID
            ("VK4MSL", False, 10),
            # Now should be the "alt-nets"
            ("VK4BWI", False, None),
        ]
    )


def test_constructor_bind_override():
    """
    Test the constructor allows overriding the usual addresses.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(
        ax25int,
        "VK4MSL-10",
        listen_destinations=[dict(callsign="APRS", regex=False, ssid=None)],
    )
    assert aprsint
    assert len(ax25int.bind_calls) == 2

    assert set(
        [
            (call, regex, ssid)
            for (cb, call, ssid, regex) in ax25int.bind_calls
        ]
    ) == set(
        [
            # The first bind call should be for the station SSID
            ("VK4MSL", False, 10),
            # The rest should be the ones we gave
            ("APRS", False, None),
        ]
    )


def test_transmit_exception():
    """
    Test that transmit swallows exceptions.
    """
    ax25int = DummyAX25Interface()

    # Stub the transmit so it fails
    calls = []

    def stub(*args):
        calls.append(args)
        raise RuntimeError("Oopsie")

    ax25int.transmit = stub

    aprsint = APRSInterface(ax25int, "VK4MSL-10")
    aprsint.transmit(
        APRSMessageFrame(
            destination="VK4BWI-2",
            source="VK4MSL-10",
            addressee="VK4BWI-2",
            message=b"testing",
            msgid=123,
        )
    )

    # Transmit should have been called
    assert len(calls) == 1


def test_send_message_oneshot():
    """
    Test that send_message in one-shot mode generates a message frame.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")
    res = aprsint.send_message("VK4MDL-7", "Hi", oneshot=True)

    # We don't get a return value
    assert res is None

    # No message handler should be registered with the interface
    assert len(aprsint._pending_msg) == 0

    # The frame is passed to the AX.25 interface
    assert len(ax25int.transmitted) == 1
    frame = ax25int.transmitted.pop(0)

    # Frame is a APRS message frame
    assert isinstance(frame, APRSMessageFrame)

    # There is no pending messages
    assert len(aprsint._pending_msg) == 0


def test_send_message_oneshot_replyack():
    """
    Test that send_message in one-shot mode refuses to send reply-ack.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")
    try:
        aprsint.send_message(
            "VK4MDL-7",
            "Hi",
            oneshot=True,
            replyack="This should be a message, but the code only tests "
            "that this value is None, which it won't be here.",
        )
    except ValueError as e:
        assert str(e) == "Cannot send reply-ack in one-shot mode"


def test_send_message_replyack():
    """
    Test that send_message with a replyack message sets replyack.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")
    replymsg = APRSMessageFrame(
        destination="APRS",
        source="VK4MDL-7",
        addressee="VK4MSL-7",
        message="Hello",
        msgid="123",
        replyack=True,
    )
    res = aprsint.send_message(
        "VK4MDL-7", "Hi", oneshot=False, replyack=replymsg
    )

    # We got back a handler class
    assert isinstance(res, APRSMessageHandler)

    # That message handler should be registered with the interface
    assert len(aprsint._pending_msg) == 1
    assert res.msgid in aprsint._pending_msg
    assert aprsint._pending_msg[res.msgid] is res

    # The APRS message handler will have tried sending the message
    assert len(ax25int.transmitted) == 1
    frame = ax25int.transmitted.pop(0)

    # Frame is a APRS message frame
    assert isinstance(frame, APRSMessageFrame)

    # Frame has reply-ACK set
    assert frame.replyack == "123"

    # Message handler is in 'SEND' state
    assert res.state == APRSMessageHandler.HandlerState.SEND


def test_send_message_advreplyack():
    """
    Test that send_message with replyack=True message sets replyack.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")
    res = aprsint.send_message("VK4MDL-7", "Hi", oneshot=False, replyack=True)

    # We got back a handler class
    assert isinstance(res, APRSMessageHandler)

    # That message handler should be registered with the interface
    assert len(aprsint._pending_msg) == 1
    assert res.msgid in aprsint._pending_msg
    assert aprsint._pending_msg[res.msgid] is res

    # The APRS message handler will have tried sending the message
    assert len(ax25int.transmitted) == 1
    frame = ax25int.transmitted.pop(0)

    # Frame is a APRS message frame
    assert isinstance(frame, APRSMessageFrame)

    # Frame has reply-ACK set
    assert frame.replyack == True

    # Message handler is in 'SEND' state
    assert res.state == APRSMessageHandler.HandlerState.SEND


def test_send_message_replyack_notreplyack():
    """
    Test that send_message in confirmable mode generates a message handler.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")
    replymsg = APRSMessageFrame(
        destination="APRS",
        source="VK4MDL-7",
        addressee="VK4MSL-7",
        message="Hello",
        msgid="123",
        replyack=False,
    )
    try:
        aprsint.send_message(
            "VK4MDL-7", "Hi", oneshot=False, replyack=replymsg
        )
    except ValueError as e:
        assert str(e) == "replyack is not a reply-ack message"


def test_send_message_confirmable():
    """
    Test that send_message in confirmable mode generates a message handler.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")
    res = aprsint.send_message("VK4MDL-7", "Hi", oneshot=False)

    # We got back a handler class
    assert isinstance(res, APRSMessageHandler)

    # That message handler should be registered with the interface
    assert len(aprsint._pending_msg) == 1
    assert res.msgid in aprsint._pending_msg
    assert aprsint._pending_msg[res.msgid] is res

    # The APRS message handler will have tried sending the message
    assert len(ax25int.transmitted) == 1
    frame = ax25int.transmitted.pop(0)

    # Frame is a APRS message frame
    assert isinstance(frame, APRSMessageFrame)

    # Message handler is in 'SEND' state
    assert res.state == APRSMessageHandler.HandlerState.SEND


def test_send_response_oneshot():
    """
    Test that send_response ignores one-shot messages.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")
    aprsint.send_response(
        APRSMessageFrame(
            destination="VK4BWI-2",
            source="VK4MSL-10",
            addressee="VK4BWI-2",
            message=b"testing",
            msgid=None,
        )
    )

    # Nothing should be sent
    assert len(ax25int.transmitted) == 0


def test_send_response_ack():
    """
    Test that send_response with ack=True sends acknowledgement.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")
    aprsint.send_response(
        APRSMessageFrame(
            destination="VK4BWI-2",
            source="VK4MSL-10",
            addressee="VK4BWI-2",
            message=b"testing",
            msgid=123,
        ),
        ack=True,
    )

    # The APRS message handler will have tried sending the message
    assert len(ax25int.transmitted) == 1
    frame = ax25int.transmitted.pop(0)

    # Frame is a APRS message acknowledgement frame
    assert isinstance(frame, APRSMessageFrame)
    assert frame.payload == b":VK4MSL-10:ack123"


def test_send_response_rej():
    """
    Test that send_response with ack=False sends rejection.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")
    aprsint.send_response(
        APRSMessageFrame(
            destination="VK4BWI-2",
            source="VK4MSL-10",
            addressee="VK4BWI-2",
            message=b"testing",
            msgid=123,
        ),
        ack=False,
    )

    # The APRS message handler will have tried sending the message
    assert len(ax25int.transmitted) == 1
    frame = ax25int.transmitted.pop(0)

    # Frame is a APRS message rejection frame
    assert isinstance(frame, APRSMessageFrame)
    assert frame.payload == b":VK4MSL-10:rej123"


def test_hash_frame_mismatch_dest():
    """
    Test that _hash_frame returns different hashes for mismatching destination
    """
    hash1 = APRSInterface._hash_frame(
        APRSMessageFrame(
            destination="VK4BWI-2",
            source="VK4MSL-10",
            addressee="VK4BWI-2",
            message=b"testing",
            msgid=123,
            repeaters=["WIDE2-1", "WIDE1-1"],
        )
    )

    hash2 = APRSInterface._hash_frame(
        APRSMessageFrame(
            destination="VK4BWI-3",
            source="VK4MSL-10",
            addressee="VK4BWI-2",
            message=b"testing",
            msgid=123,
            repeaters=["WIDE2-1", "WIDE1-1"],
        )
    )

    # These should not be the same
    assert hash1 != hash2


def test_hash_frame_mismatch_src():
    """
    Test that _hash_frame returns different hashes for mismatching source
    """
    hash1 = APRSInterface._hash_frame(
        APRSMessageFrame(
            destination="VK4BWI-2",
            source="VK4MSL-10",
            addressee="VK4BWI-2",
            message=b"testing",
            msgid=123,
            repeaters=["WIDE2-1", "WIDE1-1"],
        )
    )

    hash2 = APRSInterface._hash_frame(
        APRSMessageFrame(
            destination="VK4BWI-2",
            source="VK4MSL-11",
            addressee="VK4BWI-2",
            message=b"testing",
            msgid=123,
            repeaters=["WIDE2-1", "WIDE1-1"],
        )
    )

    # These should not be the same
    assert hash1 != hash2


def test_hash_frame_mismatch_payload():
    """
    Test that _hash_frame returns different hashes for mismatching source
    """
    hash1 = APRSInterface._hash_frame(
        APRSMessageFrame(
            destination="VK4BWI-2",
            source="VK4MSL-10",
            addressee="VK4BWI-2",
            message=b"testing 1",
            msgid=123,
            repeaters=["WIDE2-1", "WIDE1-1"],
        )
    )

    hash2 = APRSInterface._hash_frame(
        APRSMessageFrame(
            destination="VK4BWI-2",
            source="VK4MSL-10",
            addressee="VK4BWI-2",
            message=b"testing 2",
            msgid=123,
            repeaters=["WIDE2-1", "WIDE1-1"],
        )
    )

    # These should not be the same
    assert hash1 != hash2


def test_hash_frame():
    """
    Test that _hash_frame returns a consistent result regardless of digipeaters
    """
    hash1 = APRSInterface._hash_frame(
        APRSMessageFrame(
            destination="VK4BWI-2",
            source="VK4MSL-10",
            addressee="VK4BWI-2",
            message=b"testing",
            msgid=123,
            repeaters=["WIDE2-1", "WIDE1-1"],
        )
    )

    hash2 = APRSInterface._hash_frame(
        APRSMessageFrame(
            destination="VK4BWI-2",
            source="VK4MSL-10",
            addressee="VK4BWI-2",
            message=b"testing",
            msgid=123,
            repeaters=["VK4RZB*", "WIDE1-1"],
        )
    )

    hash3 = APRSInterface._hash_frame(
        APRSMessageFrame(
            destination="VK4BWI-2",
            source="VK4MSL-10",
            addressee="VK4BWI-2",
            message=b"testing",
            msgid=123,
            repeaters=["VK4RZB*", "VK4RZA*"],
        )
    )

    # These should all be the same
    assert hash1 == hash2
    assert hash1 == hash3


def test_test_or_add_frame_first():
    """
    Test that _test_or_add_frame returns False for new traffic
    """
    frame = APRSMessageFrame(
        destination="VK4BWI-2",
        source="VK4MSL-10",
        addressee="VK4BWI-2",
        message=b"testing",
        msgid=123,
        repeaters=["WIDE2-1", "WIDE1-1"],
    )
    framedigest = APRSInterface._hash_frame(frame)

    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")

    # Try it out
    res = aprsint._test_or_add_frame(frame)

    # We should get 'False' as the response
    assert res == False

    # There should be an entry in our hash table.
    assert len(aprsint._msg_expiry) == 1

    # The expiry time should be at least 25 seconds.
    assert aprsint._msg_expiry.get(framedigest, 0) > (
        ax25int._loop.time() + 25
    )

    # A clean-up should have been scheduled.
    assert len(ax25int._loop.calls) == 1
    (_, callfunc) = ax25int._loop.calls.pop(0)
    assert callfunc == aprsint._schedule_dedup_cleanup


def test_test_or_add_frame_repeat():
    """
    Test that _test_or_add_frame returns True for un-expired repeats
    """
    frame = APRSMessageFrame(
        destination="VK4BWI-2",
        source="VK4MSL-10",
        addressee="VK4BWI-2",
        message=b"testing",
        msgid=123,
        repeaters=["WIDE2-1", "WIDE1-1"],
    )
    framedigest = APRSInterface._hash_frame(frame)

    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")
    # Inject the frame expiry
    expiry_time = aprsint._loop.time() + 1
    aprsint._msg_expiry[framedigest] = expiry_time

    # Try it out
    res = aprsint._test_or_add_frame(frame)

    # We should get 'False' as the response
    assert res == True

    # Expiry should not have changed
    assert len(aprsint._msg_expiry) == 1
    assert aprsint._msg_expiry[framedigest] == expiry_time

    # Nothing further should be done.
    assert len(ax25int._loop.calls) == 0


def test_test_or_add_frame_expired():
    """
    Test that _test_or_add_frame returns False for expired repeats
    """
    frame = APRSMessageFrame(
        destination="VK4BWI-2",
        source="VK4MSL-10",
        addressee="VK4BWI-2",
        message=b"testing",
        msgid=123,
        repeaters=["WIDE2-1", "WIDE1-1"],
    )
    framedigest = APRSInterface._hash_frame(frame)

    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")
    # Inject the frame expiry
    expiry_time = aprsint._loop.time() - 1
    aprsint._msg_expiry[framedigest] = expiry_time

    # Try it out
    res = aprsint._test_or_add_frame(frame)

    # We should get 'False' as the response
    assert res == False

    # The expiry time should be at least 25 seconds.
    assert len(aprsint._msg_expiry) == 1
    assert aprsint._msg_expiry.get(framedigest, 0) > (
        ax25int._loop.time() + 25
    )

    # A clean-up should have been scheduled.
    assert len(ax25int._loop.calls) == 1
    (_, callfunc) = ax25int._loop.calls.pop(0)
    assert callfunc == aprsint._schedule_dedup_cleanup


def test_schedule_dedup_cleanup_no_msg():
    """
    Test _schedule_dedup_cleanup does nothing if no messages
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")

    aprsint._schedule_dedup_cleanup()

    # A clean-up should not have been scheduled.
    assert len(ax25int._loop.calls) == 0


def test_schedule_dedup_cleanup_pending():
    """
    Test _schedule_dedup_cleanup cancels existing pending clean-ups
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")

    # Inject a pending clean-up
    deduplication_timeout = aprsint._loop.call_later(1, None)
    aprsint._deduplication_timeout = deduplication_timeout

    # Schedule the next one
    aprsint._schedule_dedup_cleanup()

    # We should now no-longer have a pending clean-up
    assert deduplication_timeout.cancelled()
    assert aprsint._deduplication_timeout is None


def test_schedule_dedup_cleanup_oldest_future():
    """
    Test _schedule_dedup_cleanup schedules for expiry of oldest message
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")

    # Inject a few hashes
    now = aprsint._loop.time()
    aprsint._msg_expiry.update(
        {b"hash1": now + 1, b"hash2": now + 2, b"hash3": now + 3}
    )

    # Schedule the clean-up
    aprsint._schedule_dedup_cleanup()

    # A clean-up should have been scheduled.
    assert len(ax25int._loop.calls) == 1
    (calltime, callfunc) = ax25int._loop.calls.pop(0)

    # Should be scheduled for the earliest expiry
    assert (calltime - now) < (1.01)
    assert (calltime - now) > (0.99)
    assert callfunc == aprsint._dedup_cleanup


def test_schedule_dedup_cleanup_oldest_past():
    """
    Test _schedule_dedup_cleanup schedules immediately for expired messages.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")

    # Inject a few hashes
    now = aprsint._loop.time()
    aprsint._msg_expiry.update(
        {b"hash1": now - 1, b"hash2": now + 2, b"hash3": now + 3}
    )

    # Schedule the clean-up
    aprsint._schedule_dedup_cleanup()

    # A clean-up should have been scheduled.
    assert len(ax25int._loop.calls) == 1
    (calltime, callfunc) = ax25int._loop.calls.pop(0)

    # Should be scheduled pretty much now
    assert (calltime - now) < (0.01)
    assert callfunc == aprsint._dedup_cleanup


def test_dedup_cleanup_expired():
    """
    Test _dedup_cleanup removes only expired messages
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")

    # Inject a few hashes
    now = aprsint._loop.time()
    aprsint._msg_expiry.update(
        {b"hash1": now - 1, b"hash2": now + 2, b"hash3": now + 3}
    )

    # Perform the clean-up
    aprsint._dedup_cleanup()

    # We should no longer have 'hash1'
    assert b"hash1" not in aprsint._msg_expiry

    # but should have the others
    assert b"hash2" in aprsint._msg_expiry
    assert b"hash3" in aprsint._msg_expiry

    # There should be a re-schedule pending
    assert len(ax25int._loop.calls) == 1
    (calltime, callfunc) = ax25int._loop.calls.pop(0)

    # Should be scheduled pretty much now
    assert (calltime - now) < (0.01)
    assert callfunc == aprsint._schedule_dedup_cleanup


def test_on_receive_exception():
    """
    Test _on_receive swallows exceptions.
    """
    # Create a frame
    frame = AX25UnnumberedInformationFrame(
        destination="VK4BWI-2",
        source="VK4MSL-10",
        pid=0xF0,
        payload=b":VK4BWI-2 :testing{123",
        repeaters=["WIDE2-1", "WIDE1-1"],
    )

    # Create our interface
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")

    # Stub the _test_or_add_frame so it returns false
    aprsint._test_or_add_frame = lambda *a: False

    # Stub the IOLoop's call_soon so it fails
    calls = []

    def stub(*args):
        calls.append(args)
        raise RuntimeError("Oopsie")

    aprsint._loop.call_soon = stub

    # Now pass the frame in as if it were just received
    aprsint._on_receive(frame)

    # We should have called call_soon, but the exception should have been
    # caught and logged.
    assert len(calls) == 1


def test_on_receive_notframe():
    """
    Test _on_receive ignores non-APRS-frames.
    """

    # Create a frame
    class DummyFrame(AX25UnnumberedInformationFrame):
        def __init__(self, *args, **kwargs):
            self.addressee_calls = 0
            super(DummyFrame, self).__init__(*args, **kwargs)

        @property
        def addressee(self):
            self.addressee_calls += 1
            return AX25Address.decode("N0CALL")

    frame = DummyFrame(
        destination="VK4BWI-2",
        source="VK4MSL-10",
        pid=0xF0,
        payload=b"this is not an APRS message",
        repeaters=["WIDE2-1", "WIDE1-1"],
    )

    # Create our interface
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")

    # Stub the _test_or_add_frame so it returns false
    aprsint._test_or_add_frame = lambda *a: False

    # Now pass the frame in as if it were just received
    aprsint._on_receive(frame)

    # The addressee property should not be touched
    assert frame.addressee_calls == 0


def test_on_receive_dup():
    """
    Test _on_receive ignores duplicate frames.
    """
    # Create a frame and hash it
    frame = AX25UnnumberedInformationFrame(
        destination="VK4BWI-2",
        source="VK4MSL-10",
        pid=0xF0,
        payload=b":VK4BWI-2 :testing{123",
        repeaters=["WIDE2-1", "WIDE1-1"],
    )
    framedigest = APRSInterface._hash_frame(frame)

    # Create our interface
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")

    # Inject the hash
    now = aprsint._loop.time()
    aprsint._msg_expiry.update({framedigest: now + 3})

    # Now pass the frame in as if it were just received
    aprsint._on_receive(frame)

    # There should be no calls made
    assert len(ax25int._loop.calls) == 0


def test_on_receive_pass_to_router():
    """
    Test _on_receive passes the message to the base APRSRouter class.
    """
    # Create a frame
    frame = AX25UnnumberedInformationFrame(
        destination="VK4BWI-2",
        source="VK4MSL-10",
        pid=0xF0,
        payload=b":VK4BWI-2 :testing{123",
        repeaters=["WIDE2-1", "WIDE1-1"],
    )

    # Create our interface
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")

    # Now pass the frame in as if it were just received
    aprsint._on_receive(frame)

    # There should be two calls made, one to our deduplication clean-up, the
    # other to our superclass
    assert len(ax25int._loop.calls) == 2

    (_, callfunc) = ax25int._loop.calls.pop(0)
    assert callfunc == aprsint._schedule_dedup_cleanup

    (_, callfunc) = ax25int._loop.calls.pop(0)
    assert isinstance(callfunc, partial)
    assert callfunc.func == super(APRSInterface, aprsint)._on_receive


def test_on_receive_addressed():
    """
    Test _on_receive of message addressed to station.
    """
    # Create a frame
    frame = AX25UnnumberedInformationFrame(
        destination="APZAIO",
        source="VK4BWI-2",
        pid=0xF0,
        payload=b":VK4MSL-10:testing{123",
        repeaters=["WIDE2-1", "WIDE1-1"],
    )

    # Create our interface
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")

    # Now pass the frame in as if it were just received
    aprsint._on_receive(frame)

    # There should be three calls made, one to our deduplication clean-up, the
    # other to our superclass, the third to our received_address_msg signal.
    assert len(ax25int._loop.calls) == 3

    (_, callfunc) = ax25int._loop.calls.pop(0)
    assert callfunc == aprsint._schedule_dedup_cleanup

    (_, callfunc) = ax25int._loop.calls.pop(0)
    assert isinstance(callfunc, partial)
    assert callfunc.func == super(APRSInterface, aprsint)._on_receive

    (_, callfunc) = ax25int._loop.calls.pop(0)
    assert isinstance(callfunc, partial)
    assert callfunc.func == aprsint.received_addressed_msg.emit


def test_on_receive_addressed_replyack():
    """
    Test _on_receive of message addressed to station advertising reply-ack.
    """
    # Create a frame
    frame = AX25UnnumberedInformationFrame(
        destination="APZAIO",
        source="VK4BWI-2",
        pid=0xF0,
        payload=b":VK4MSL-10:testing{123}",
        repeaters=["WIDE2-1", "WIDE1-1"],
    )

    # Create our interface
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")

    # Now pass the frame in as if it were just received
    aprsint._on_receive(frame)

    # There should be three calls made, one to our deduplication clean-up, the
    # other to our superclass, the third to our received_address_msg signal.
    assert len(ax25int._loop.calls) == 3

    (_, callfunc) = ax25int._loop.calls.pop(0)
    assert callfunc == aprsint._schedule_dedup_cleanup

    (_, callfunc) = ax25int._loop.calls.pop(0)
    assert isinstance(callfunc, partial)
    assert callfunc.func == super(APRSInterface, aprsint)._on_receive

    (_, callfunc) = ax25int._loop.calls.pop(0)
    assert isinstance(callfunc, partial)
    assert callfunc.func == aprsint.received_addressed_msg.emit


def test_on_receive_unsol_ackrej():
    """
    Test _on_receive of unsolicited ACK/REJ addressed to station.
    """
    # Create a frame
    frame = AX25UnnumberedInformationFrame(
        destination="APZAIO",
        source="VK4BWI-2",
        pid=0xF0,
        payload=b":VK4MSL-10:ack123",
        repeaters=["WIDE2-1", "WIDE1-1"],
    )

    # Create our interface
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")

    # Now pass the frame in as if it were just received
    aprsint._on_receive(frame)

    # There should be two calls made, one to our deduplication clean-up, the
    # other to our superclass.  We don't pass the message out otherwise.
    assert len(ax25int._loop.calls) == 2

    (_, callfunc) = ax25int._loop.calls.pop(0)
    assert callfunc == aprsint._schedule_dedup_cleanup

    (_, callfunc) = ax25int._loop.calls.pop(0)
    assert isinstance(callfunc, partial)
    assert callfunc.func == super(APRSInterface, aprsint)._on_receive


def test_on_receive_sol_ackrej():
    """
    Test _on_receive of solicited ACK/REJ addressed to station.
    """
    # Create a frame
    frame = AX25UnnumberedInformationFrame(
        destination="APZAIO",
        source="VK4BWI-2",
        pid=0xF0,
        payload=b":VK4MSL-10:ack123",
        repeaters=["WIDE2-1", "WIDE1-1"],
    )

    # Create our interface
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")

    # Inject a message handler for the message ID
    handler = DummyMessageHandler()
    aprsint._pending_msg["123"] = handler

    # Now pass the frame in as if it were just received
    aprsint._on_receive(frame)

    # There should be three calls made, one to our deduplication clean-up, the
    # second to our superclass, and finally the third to the handler's
    # _on_response method.
    assert len(ax25int._loop.calls) == 3

    (_, callfunc) = ax25int._loop.calls.pop(0)
    assert callfunc == aprsint._schedule_dedup_cleanup

    (_, callfunc) = ax25int._loop.calls.pop(0)
    assert isinstance(callfunc, partial)
    assert callfunc.func == super(APRSInterface, aprsint)._on_receive

    (_, callfunc, msg) = ax25int._loop.calls.pop(0)
    assert callfunc == handler._on_response
    assert bytes(frame) == bytes(msg)


def test_on_receive_sol_replyack():
    """
    Test _on_receive of solicited reply-ack addressed to station.
    """
    # Create a frame
    frame = AX25UnnumberedInformationFrame(
        destination="APZAIO",
        source="VK4BWI-2",
        pid=0xF0,
        payload=b":VK4MSL-10:testing{356}123",
        repeaters=["WIDE2-1", "WIDE1-1"],
    )

    # Create our interface
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")

    # Inject a message handler for the message ID
    handler = DummyMessageHandler()
    aprsint._pending_msg["123"] = handler

    # Now pass the frame in as if it were just received
    aprsint._on_receive(frame)

    # There should be four calls made, one to our deduplication clean-up, the
    # second to our superclass, the third to the handler's _on_response method
    # and finally the incoming message should be emitted like a normal message.
    assert len(ax25int._loop.calls) == 4

    (_, callfunc) = ax25int._loop.calls.pop(0)
    assert callfunc == aprsint._schedule_dedup_cleanup

    (_, callfunc) = ax25int._loop.calls.pop(0)
    assert isinstance(callfunc, partial)
    assert callfunc.func == super(APRSInterface, aprsint)._on_receive

    (_, callfunc, msg) = ax25int._loop.calls.pop(0)
    assert callfunc == handler._on_response
    assert bytes(frame) == bytes(msg)

    # The message should also have been treated as a new incoming message.
    (_, callfunc) = ax25int._loop.calls.pop(0)
    assert isinstance(callfunc, partial)
    assert callfunc.func == aprsint.received_addressed_msg.emit


def test_on_msg_handler_finish():
    """
    Test that _on_msg_handler_finish removes a message from the pending list
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, "VK4MSL-10")

    # Inject a message handler for the message ID
    handler = DummyMessageHandler()
    aprsint._pending_msg["123"] = handler

    # Call the clean-up function
    aprsint._on_msg_handler_finish("123")

    # This should now be empty
    assert aprsint._pending_msg == {}
