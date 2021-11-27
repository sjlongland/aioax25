#!/usr/bin/env python3

"""
KISS protocol unit tests.
"""

from aioax25 import kiss
import logging
import time


class DummyTransport(object):
    def __init__(self):
        self.closed = False

    def close(self):
        assert self.closed is False, 'Already closed'
        self.closed = True


class TestError(Exception):
    pass


def test_protocol_connection_made(logger):
    """
    Test connection_made calls the _on_connect call-back.
    """
    on_connect_calls = []
    transport = DummyTransport()


    def on_connect(*args, **kwargs):
        on_connect_calls.append((args, kwargs))

    def on_receive(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_close(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    protocol = kiss.KISSProtocol(on_connect, on_receive, on_close, logger)
    protocol.connection_made(transport)

    assert on_connect_calls == [((transport,), {})]
    assert transport.closed is False
    assert logger.logrecords == []
    assert logger.children == {}


def test_protocol_connection_made_err(logger):
    """
    Test connection_made handles errors.
    """
    on_connect_calls = []
    transport = DummyTransport()

    def on_connect(*args, **kwargs):
        on_connect_calls.append((args, kwargs))
        raise TestError()

    def on_receive(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_close(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    protocol = kiss.KISSProtocol(on_connect, on_receive, on_close, logger)
    protocol.connection_made(transport)

    assert logger.children == {}
    assert len(logger.logrecords) > 0
    assert logger.logrecords[1:] == []

    log = logger.logrecords[0]
    assert log.pop('ex_type', None) == TestError
    log.pop('ex_val', None)
    log.pop('ex_tb', None)

    assert log == dict(
        method='exception',
        args=('Failed to handle connection establishment',),
        kwargs={}
    )


def test_protocol_data_received(logger):
    """
    Test data_received calls the _on_connect call-back.
    """
    on_receive_calls = []
    received_data = b'Dummy received data'

    def on_connect(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_receive(*args, **kwargs):
        on_receive_calls.append((args, kwargs))

    def on_close(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    protocol = kiss.KISSProtocol(on_connect, on_receive, on_close,
            logging.getLogger('%s.data_received' % __name__))

    protocol.data_received(received_data)

    assert on_receive_calls == [((received_data,), {})]
    assert logger.logrecords == []
    assert logger.children == {}


def test_protocol_data_received_err(logger):
    """
    Test data_received handles errors.
    """
    on_receive_calls = []
    received_data = b'Dummy received data'

    def on_connect(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_receive(*args, **kwargs):
        on_receive_calls.append((args, kwargs))
        raise TestError()

    def on_close(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    protocol = kiss.KISSProtocol(on_connect, on_receive, on_close, logger)
    protocol.data_received(received_data)

    assert on_receive_calls == [((received_data,), {})]
    assert logger.children == {}
    assert len(logger.logrecords) > 0
    assert logger.logrecords[1:] == []

    log = logger.logrecords[0]
    assert log.pop('ex_type', None) == TestError
    log.pop('ex_val', None)
    log.pop('ex_tb', None)

    assert log == dict(
        method='exception',
        args=('Failed to handle incoming data',),
        kwargs={}
    )


def test_protocol_connection_lost(logger):
    """
    Test connection_lost calls the _on_connect call-back.
    """
    on_close_calls = []
    loss_err = TestError()

    def on_connect(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_receive(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_close(*args, **kwargs):
        on_close_calls.append((args, kwargs))

    protocol = kiss.KISSProtocol(on_connect, on_receive, on_close, logger)
    protocol.connection_lost(loss_err)

    assert on_close_calls == [((loss_err,), {})]
    assert logger.logrecords == []
    assert logger.children == {}


def test_protocol_connection_lost_err(logger):
    """
    Test connection_lost handles errors.
    """
    class TestConnectionLossError(Exception):
        pass

    on_close_calls = []
    loss_err = TestConnectionLossError()

    def on_connect(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_receive(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_close(*args, **kwargs):
        on_close_calls.append((args, kwargs))
        raise TestError()

    protocol = kiss.KISSProtocol(on_connect, on_receive, on_close, logger)
    protocol.connection_lost(loss_err)

    assert on_close_calls == [((loss_err,), {})]
    assert logger.children == {}
    assert len(logger.logrecords) > 0
    assert logger.logrecords[1:] == []

    log = logger.logrecords[0]
    assert log.pop('ex_type', None) == TestError
    log.pop('ex_val', None)
    log.pop('ex_tb', None)

    assert log == dict(
        method='exception',
        args=('Failed to handle connection loss',),
        kwargs={}
    )


def test_subproc_protocol_connection_made(logger):
    """
    Test connection_made calls the _on_connect call-back.
    """
    on_connect_calls = []
    transport = DummyTransport()


    def on_connect(*args, **kwargs):
        on_connect_calls.append((args, kwargs))

    def on_receive(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_close(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    protocol = kiss.KISSSubprocessProtocol(on_connect, on_receive, on_close, logger)
    protocol.connection_made(transport)

    assert on_connect_calls == [((transport,), {})]
    assert transport.closed is False
    assert logger.logrecords == []
    assert logger.children == {}


def test_subproc_protocol_connection_made_err(logger):
    """
    Test connection_made handles errors.
    """
    on_connect_calls = []
    transport = DummyTransport()

    def on_connect(*args, **kwargs):
        on_connect_calls.append((args, kwargs))
        raise TestError()

    def on_receive(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_close(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    protocol = kiss.KISSSubprocessProtocol(on_connect, on_receive, on_close, logger)
    protocol.connection_made(transport)

    assert logger.children == {}
    assert len(logger.logrecords) > 0
    assert logger.logrecords[1:] == []

    log = logger.logrecords[0]
    assert log.pop('ex_type', None) == TestError
    log.pop('ex_val', None)
    log.pop('ex_tb', None)

    assert log == dict(
        method='exception',
        args=('Failed to handle connection establishment',),
        kwargs={}
    )


def test_subproc_protocol_pipe_data_received_stdout(logger):
    """
    Test pipe_data_received calls the _on_connect call-back for stdout.
    """
    on_receive_calls = []
    received_data = b'Dummy received data'

    def on_connect(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_receive(*args, **kwargs):
        on_receive_calls.append((args, kwargs))

    def on_close(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    protocol = kiss.KISSSubprocessProtocol(
            on_connect, on_receive, on_close, logger
    )
    protocol.pipe_data_received(1, received_data)

    assert on_receive_calls == [((received_data,), {})]
    assert logger.logrecords == []
    assert logger.children == {}


def test_subproc_protocol_pipe_data_received_stderr(logger):
    """
    Test pipe_data_received ignores data received on stderr.
    """
    on_receive_calls = []
    received_data = b'Dummy received data'

    def on_connect(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_receive(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_close(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    protocol = kiss.KISSSubprocessProtocol(
            on_connect, on_receive, on_close, logger
    )
    protocol.pipe_data_received(2, received_data)

    assert on_receive_calls == []
    assert logger.children == {}
    assert logger.logrecords == [
            dict(
                method='debug',
                args=(
                    'Data received on fd=%d: %r',
                    2, received_data
                ),
                kwargs={},
                ex_type=None, ex_val=None, ex_tb=None
            )
    ]


def test_subproc_protocol_pipe_data_received_err(logger):
    """
    Test pipe_data_received handles errors.
    """
    on_receive_calls = []
    received_data = b'Dummy received data'

    def on_connect(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_receive(*args, **kwargs):
        on_receive_calls.append((args, kwargs))
        raise TestError()

    def on_close(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    protocol = kiss.KISSSubprocessProtocol(on_connect, on_receive, on_close, logger)
    protocol.pipe_data_received(1, received_data)

    assert on_receive_calls == [((received_data,), {})]
    assert logger.children == {}
    assert len(logger.logrecords) > 0
    assert logger.logrecords[1:] == []

    log = logger.logrecords[0]
    assert log.pop('ex_type', None) == TestError
    log.pop('ex_val', None)
    log.pop('ex_tb', None)

    assert log == dict(
        method='exception',
        args=(
            'Failed to handle incoming data %r on fd=%d',
            received_data, 1
        ),
        kwargs={}
    )


def test_subproc_protocol_process_exited(logger):
    """
    Test process_exited calls the _on_connect call-back.
    """
    on_close_calls = []

    def on_connect(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_receive(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_close(*args, **kwargs):
        on_close_calls.append((args, kwargs))

    protocol = kiss.KISSSubprocessProtocol(
            on_connect, on_receive, on_close, logger
    )

    protocol.process_exited()

    assert on_close_calls == [((None,), {})]
    assert logger.logrecords == []
    assert logger.children == {}


def test_subproc_protocol_process_exited_err(logger):
    """
    Test process_exited handles errors.
    """
    class TestConnectionLossError(Exception):
        pass

    on_close_calls = []
    loss_err = TestConnectionLossError()

    def on_connect(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_receive(*args, **kwargs):
        assert False, \
                'Should not have been called (called with %r, %r)' \
                % (args, kwargs)

    def on_close(*args, **kwargs):
        on_close_calls.append((args, kwargs))
        raise TestError()

    protocol = kiss.KISSSubprocessProtocol(on_connect, on_receive, on_close, logger)
    protocol.process_exited()

    assert on_close_calls == [((None,), {})]
    assert logger.children == {}
    assert len(logger.logrecords) > 0
    assert logger.logrecords[1:] == []

    log = logger.logrecords[0]
    assert log.pop('ex_type', None) == TestError
    log.pop('ex_val', None)
    log.pop('ex_tb', None)

    assert log == dict(
        method='exception',
        args=('Failed to handle process exit',),
        kwargs={}
    )
