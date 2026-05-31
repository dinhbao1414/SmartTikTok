import asyncio
import json
import unittest

from websockets.protocol import State

from remote_browser.cdp.connection import CDPConnection


class Websockets16ConnectionStub:
    def __init__(self, state=State.OPEN):
        self.state = state
        self.sent_messages = []
        self.close_calls = 0

    async def send(self, message):
        self.sent_messages.append(json.loads(message))

    async def close(self):
        self.close_calls += 1
        self.state = State.CLOSED


class RemoteBrowserConnectionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.loop = asyncio.get_running_loop()

    async def test_send_accepts_websockets_16_state_connection(self):
        transport = Websockets16ConnectionStub(State.OPEN)
        connection = CDPConnection("ws://example.test", self.loop, "test-session")
        connection.connection = transport

        result = await connection.send("Browser.getVersion", timeout=0.01)

        self.assertIsNone(result)
        self.assertEqual(transport.sent_messages[0]["method"], "Browser.getVersion")
        self.assertEqual(connection.pending_responses, {})

    async def test_send_skips_websockets_16_closed_state_connection(self):
        transport = Websockets16ConnectionStub(State.CLOSED)
        connection = CDPConnection("ws://example.test", self.loop, "test-session")
        connection.connection = transport

        await connection.send("Browser.getVersion", timeout=0.01)

        self.assertEqual(transport.sent_messages, [])

    async def test_cleanup_closes_websockets_16_state_connection(self):
        transport = Websockets16ConnectionStub(State.OPEN)
        connection = CDPConnection("ws://example.test", self.loop, "test-session")
        connection.connection = transport

        await connection.cleanup_connection()

        self.assertEqual(transport.close_calls, 1)
        self.assertEqual(transport.state, State.CLOSED)


if __name__ == "__main__":
    unittest.main()
