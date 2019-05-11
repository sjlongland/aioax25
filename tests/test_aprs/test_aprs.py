#!/usr/bin/env python3

from nose.tools import eq_, assert_set_equal, assert_is, assert_greater, \
        assert_less

from aioax25.aprs import APRSInterface
from aioax25.aprs.message import APRSMessageFrame, APRSMessageHandler

from ..loop import DummyLoop


class DummyAX25Interface(object):
    def __init__(self):
        self._loop = DummyLoop()
        self.bind_calls = []
        self.transmitted = []

    def bind(self, callback, callsign, ssid=0, regex=False):
        self.bind_calls.append((callback, callsign, ssid, regex))

    def transmit(self, frame):
        self.transmitted.append(frame)


def test_constructor_bind():
    """
    Test the constructor binds to the usual destination addresses.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, 'VK4MSL-10')
    eq_(len(ax25int.bind_calls), 26)

    assert_set_equal(
            set([
                (call, regex, ssid)
                for (cb, call, ssid, regex)
                in ax25int.bind_calls
            ]),
            set([
                # The first bind call should be for the station SSID
                ('VK4MSL',  False,  10),
                # The rest should be the standard APRS ones.
                ('^AIR',    True,   None),
                ('^ALL',    True,   None),
                ('^AP',     True,   None),
                ('BEACON',  False,  None),
                ('^CQ',     True,   None),
                ('^GPS',    True,   None),
                ('^DF',     True,   None),
                ('^DGPS',   True,   None),
                ('^DRILL',  True,   None),
                ('^ID',     True,   None),
                ('^JAVA',   True,   None),
                ('^MAIL',   True,   None),
                ('^MICE',   True,   None),
                ('^QST',    True,   None),
                ('^QTH',    True,   None),
                ('^RTCM',   True,   None),
                ('^SKY',    True,   None),
                ('^SPACE',  True,   None),
                ('^SPC',    True,   None),
                ('^SYM',    True,   None),
                ('^TEL',    True,   None),
                ('^TEST',   True,   None),
                ('^TLM',    True,   None),
                ('^WX',     True,   None),
                ('^ZIP',    True,   None)
            ])
    )

def test_constructor_bind_altnets():
    """
    Test the constructor binds to "alt-nets".
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(
            ax25int, 'VK4MSL-10',
            listen_altnets=[
                dict(callsign='VK4BWI', regex=False, ssid=None)
            ])
    eq_(len(ax25int.bind_calls), 27)

    assert_set_equal(
            set([
                (call, regex, ssid)
                for (cb, call, ssid, regex)
                in ax25int.bind_calls
            ]),
            set([
                # The first bind call should be for the station SSID
                ('VK4MSL',  False,  10),
                # The rest should be the standard APRS ones.
                ('^AIR',    True,   None),
                ('^ALL',    True,   None),
                ('^AP',     True,   None),
                ('BEACON',  False,  None),
                ('^CQ',     True,   None),
                ('^GPS',    True,   None),
                ('^DF',     True,   None),
                ('^DGPS',   True,   None),
                ('^DRILL',  True,   None),
                ('^ID',     True,   None),
                ('^JAVA',   True,   None),
                ('^MAIL',   True,   None),
                ('^MICE',   True,   None),
                ('^QST',    True,   None),
                ('^QTH',    True,   None),
                ('^RTCM',   True,   None),
                ('^SKY',    True,   None),
                ('^SPACE',  True,   None),
                ('^SPC',    True,   None),
                ('^SYM',    True,   None),
                ('^TEL',    True,   None),
                ('^TEST',   True,   None),
                ('^TLM',    True,   None),
                ('^WX',     True,   None),
                ('^ZIP',    True,   None),
                # Now should be the "alt-nets"
                ('VK4BWI',  False,  None)
            ])
    )

def test_constructor_bind_override():
    """
    Test the constructor allows overriding the usual addresses.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, 'VK4MSL-10',
            listen_destinations=[
                dict(callsign='APRS', regex=False, ssid=None)
            ])
    eq_(len(ax25int.bind_calls), 2)

    assert_set_equal(
            set([
                (call, regex, ssid)
                for (cb, call, ssid, regex)
                in ax25int.bind_calls
            ]),
            set([
                # The first bind call should be for the station SSID
                ('VK4MSL',  False,  10),
                # The rest should be the ones we gave
                ('APRS',    False,  None)
            ])
    )

def test_send_message_oneshot():
    """
    Test that send_message in one-shot mode generates a message frame.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, 'VK4MSL-10')
    res = aprsint.send_message(
            'VK4MDL-7', 'Hi', oneshot=True
    )

    # We don't get a return value
    assert_is(res, None)

    # No message handler should be registered with the interface
    eq_(len(aprsint._pending_msg), 0)

    # The frame is passed to the AX.25 interface
    eq_(len(ax25int.transmitted), 1)
    frame = ax25int.transmitted.pop(0)

    # Frame is a APRS message frame
    assert isinstance(frame, APRSMessageFrame)

    # There is no pending messages
    eq_(len(aprsint._pending_msg), 0)

def test_send_message_confirmable():
    """
    Test that send_message in confirmable mode generates a message handler.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, 'VK4MSL-10')
    res = aprsint.send_message(
            'VK4MDL-7', 'Hi', oneshot=False
    )

    # We got back a handler class
    assert isinstance(res, APRSMessageHandler)

    # That message handler should be registered with the interface
    eq_(len(aprsint._pending_msg), 1)
    assert res.msgid in aprsint._pending_msg
    assert_is(aprsint._pending_msg[res.msgid], res)

    # The APRS message handler will have tried sending the message
    eq_(len(ax25int.transmitted), 1)
    frame = ax25int.transmitted.pop(0)

    # Frame is a APRS message frame
    assert isinstance(frame, APRSMessageFrame)

    # Message handler is in 'SEND' state
    eq_(res.state, APRSMessageHandler.HandlerState.SEND)

def test_send_response_oneshot():
    """
    Test that send_response ignores one-shot messages.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, 'VK4MSL-10')
    aprsint.send_response(
            APRSMessageFrame(
                destination='VK4BWI-2',
                source='VK4MSL-10',
                addressee='VK4BWI-2',
                message=b'testing',
                msgid=None
            )
    )

    # Nothing should be sent
    eq_(len(ax25int.transmitted), 0)

def test_send_response_ack():
    """
    Test that send_response with ack=True sends acknowledgement.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, 'VK4MSL-10')
    aprsint.send_response(
            APRSMessageFrame(
                destination='VK4BWI-2',
                source='VK4MSL-10',
                addressee='VK4BWI-2',
                message=b'testing',
                msgid=123
            ),
            ack=True
    )

    # The APRS message handler will have tried sending the message
    eq_(len(ax25int.transmitted), 1)
    frame = ax25int.transmitted.pop(0)

    # Frame is a APRS message acknowledgement frame
    assert isinstance(frame, APRSMessageFrame)
    eq_(frame.payload, b':VK4MSL-10:ack123')

def test_send_response_rej():
    """
    Test that send_response with ack=False sends rejection.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, 'VK4MSL-10')
    aprsint.send_response(
            APRSMessageFrame(
                destination='VK4BWI-2',
                source='VK4MSL-10',
                addressee='VK4BWI-2',
                message=b'testing',
                msgid=123
            ),
            ack=False
    )

    # The APRS message handler will have tried sending the message
    eq_(len(ax25int.transmitted), 1)
    frame = ax25int.transmitted.pop(0)

    # Frame is a APRS message rejection frame
    assert isinstance(frame, APRSMessageFrame)
    eq_(frame.payload, b':VK4MSL-10:rej123')

def test_hash_frame_mismatch_dest():
    """
    Test that _hash_frame returns different hashes for mismatching destination
    """
    hash1 = APRSInterface._hash_frame(
            APRSMessageFrame(
                destination='VK4BWI-2',
                source='VK4MSL-10',
                addressee='VK4BWI-2',
                message=b'testing',
                msgid=123,
                repeaters=['WIDE2-1','WIDE1-1']
            )
    )

    hash2 = APRSInterface._hash_frame(
            APRSMessageFrame(
                destination='VK4BWI-3',
                source='VK4MSL-10',
                addressee='VK4BWI-2',
                message=b'testing',
                msgid=123,
                repeaters=['WIDE2-1','WIDE1-1']
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
                destination='VK4BWI-2',
                source='VK4MSL-10',
                addressee='VK4BWI-2',
                message=b'testing',
                msgid=123,
                repeaters=['WIDE2-1','WIDE1-1']
            )
    )

    hash2 = APRSInterface._hash_frame(
            APRSMessageFrame(
                destination='VK4BWI-2',
                source='VK4MSL-11',
                addressee='VK4BWI-2',
                message=b'testing',
                msgid=123,
                repeaters=['WIDE2-1','WIDE1-1']
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
                destination='VK4BWI-2',
                source='VK4MSL-10',
                addressee='VK4BWI-2',
                message=b'testing 1',
                msgid=123,
                repeaters=['WIDE2-1','WIDE1-1']
            )
    )

    hash2 = APRSInterface._hash_frame(
            APRSMessageFrame(
                destination='VK4BWI-2',
                source='VK4MSL-10',
                addressee='VK4BWI-2',
                message=b'testing 2',
                msgid=123,
                repeaters=['WIDE2-1','WIDE1-1']
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
                destination='VK4BWI-2',
                source='VK4MSL-10',
                addressee='VK4BWI-2',
                message=b'testing',
                msgid=123,
                repeaters=['WIDE2-1','WIDE1-1']
            )
    )

    hash2 = APRSInterface._hash_frame(
            APRSMessageFrame(
                destination='VK4BWI-2',
                source='VK4MSL-10',
                addressee='VK4BWI-2',
                message=b'testing',
                msgid=123,
                repeaters=['VK4RZB*','WIDE1-1']
            )
    )

    hash3 = APRSInterface._hash_frame(
            APRSMessageFrame(
                destination='VK4BWI-2',
                source='VK4MSL-10',
                addressee='VK4BWI-2',
                message=b'testing',
                msgid=123,
                repeaters=['VK4RZB*','VK4RZA*']
            )
    )

    # These should all be the same
    eq_(hash1, hash2)
    eq_(hash1, hash3)

def test_test_or_add_frame_first():
    """
    Test that _test_or_add_frame returns False for new traffic
    """
    frame = APRSMessageFrame(
                destination='VK4BWI-2',
                source='VK4MSL-10',
                addressee='VK4BWI-2',
                message=b'testing',
                msgid=123,
                repeaters=['WIDE2-1','WIDE1-1']
    )
    framedigest = APRSInterface._hash_frame(frame)

    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, 'VK4MSL-10')

    # Try it out
    res = aprsint._test_or_add_frame(frame)

    # We should get 'False' as the response
    eq_(res, False)

    # There should be an entry in our hash table.
    eq_(len(aprsint._msg_expiry), 1)

    # The expiry time should be at least 25 seconds.
    assert_greater(aprsint._msg_expiry.get(framedigest, 0),
            ax25int._loop.time() + 25)

    # A clean-up should have been scheduled.
    eq_(len(ax25int._loop.calls), 1)
    (_, callfunc) = ax25int._loop.calls.pop(0)
    eq_(callfunc, aprsint._schedule_dedup_cleanup)

def test_test_or_add_frame_repeat():
    """
    Test that _test_or_add_frame returns True for un-expired repeats
    """
    frame = APRSMessageFrame(
                destination='VK4BWI-2',
                source='VK4MSL-10',
                addressee='VK4BWI-2',
                message=b'testing',
                msgid=123,
                repeaters=['WIDE2-1','WIDE1-1']
    )
    framedigest = APRSInterface._hash_frame(frame)

    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, 'VK4MSL-10')
    # Inject the frame expiry
    expiry_time = aprsint._loop.time() + 1
    aprsint._msg_expiry[framedigest] = expiry_time

    # Try it out
    res = aprsint._test_or_add_frame(frame)

    # We should get 'False' as the response
    eq_(res, True)

    # Expiry should not have changed
    eq_(len(aprsint._msg_expiry), 1)
    eq_(aprsint._msg_expiry[framedigest], expiry_time)

    # Nothing further should be done.
    eq_(len(ax25int._loop.calls), 0)

def test_test_or_add_frame_expired():
    """
    Test that _test_or_add_frame returns False for expired repeats
    """
    frame = APRSMessageFrame(
                destination='VK4BWI-2',
                source='VK4MSL-10',
                addressee='VK4BWI-2',
                message=b'testing',
                msgid=123,
                repeaters=['WIDE2-1','WIDE1-1']
    )
    framedigest = APRSInterface._hash_frame(frame)

    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, 'VK4MSL-10')
    # Inject the frame expiry
    expiry_time = aprsint._loop.time() - 1
    aprsint._msg_expiry[framedigest] = expiry_time

    # Try it out
    res = aprsint._test_or_add_frame(frame)

    # We should get 'False' as the response
    eq_(res, False)

    # The expiry time should be at least 25 seconds.
    eq_(len(aprsint._msg_expiry), 1)
    assert_greater(aprsint._msg_expiry.get(framedigest, 0),
            ax25int._loop.time() + 25)

    # A clean-up should have been scheduled.
    eq_(len(ax25int._loop.calls), 1)
    (_, callfunc) = ax25int._loop.calls.pop(0)
    eq_(callfunc, aprsint._schedule_dedup_cleanup)

def test_schedule_dedup_cleanup_no_msg():
    """
    Test _schedule_dedup_cleanup does nothing if no messages
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, 'VK4MSL-10')

    aprsint._schedule_dedup_cleanup()

    # A clean-up should not have been scheduled.
    eq_(len(ax25int._loop.calls), 0)

def test_schedule_dedup_cleanup_pending():
    """
    Test _schedule_dedup_cleanup cancels existing pending clean-ups
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, 'VK4MSL-10')

    # Inject a pending clean-up
    deduplication_timeout = aprsint._loop.call_later(1, None)
    aprsint._deduplication_timeout = deduplication_timeout

    # Schedule the next one
    aprsint._schedule_dedup_cleanup()

    # We should now no-longer have a pending clean-up
    assert deduplication_timeout.cancelled()
    assert_is(aprsint._deduplication_timeout, None)

def test_schedule_dedup_cleanup_oldest_future():
    """
    Test _schedule_dedup_cleanup schedules for expiry of oldest message
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, 'VK4MSL-10')

    # Inject a few hashes
    now = aprsint._loop.time()
    aprsint._msg_expiry.update({
        b'hash1': now + 1,
        b'hash2': now + 2,
        b'hash3': now + 3
    })

    # Schedule the clean-up
    aprsint._schedule_dedup_cleanup()

    # A clean-up should have been scheduled.
    eq_(len(ax25int._loop.calls), 1)
    (calltime, callfunc) = ax25int._loop.calls.pop(0)

    # Should be scheduled for the earliest expiry
    assert_less(calltime - now, 1.01)
    assert_greater(calltime - now, 0.99)
    eq_(callfunc, aprsint._dedup_cleanup)

def test_schedule_dedup_cleanup_oldest_past():
    """
    Test _schedule_dedup_cleanup schedules immediately for expired messages.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, 'VK4MSL-10')

    # Inject a few hashes
    now = aprsint._loop.time()
    aprsint._msg_expiry.update({
        b'hash1': now - 1,
        b'hash2': now + 2,
        b'hash3': now + 3
    })

    # Schedule the clean-up
    aprsint._schedule_dedup_cleanup()

    # A clean-up should have been scheduled.
    eq_(len(ax25int._loop.calls), 1)
    (calltime, callfunc) = ax25int._loop.calls.pop(0)

    # Should be scheduled pretty much now
    assert_less(calltime - now, 0.01)
    eq_(callfunc, aprsint._dedup_cleanup)

def test_dedup_cleanup_expired():
    """
    Test _dedup_cleanup removes only expired messages
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, 'VK4MSL-10')

    # Inject a few hashes
    now = aprsint._loop.time()
    aprsint._msg_expiry.update({
        b'hash1': now - 1,
        b'hash2': now + 2,
        b'hash3': now + 3
    })

    # Perform the clean-up
    aprsint._dedup_cleanup()

    # We should no longer have 'hash1'
    assert b'hash1' not in aprsint._msg_expiry

    # but should have the others
    assert b'hash2' in aprsint._msg_expiry
    assert b'hash3' in aprsint._msg_expiry

    # There should be a re-schedule pending
    eq_(len(ax25int._loop.calls), 1)
    (calltime, callfunc) = ax25int._loop.calls.pop(0)

    # Should be scheduled pretty much now
    assert_less(calltime - now, 0.01)
    eq_(callfunc, aprsint._schedule_dedup_cleanup)
