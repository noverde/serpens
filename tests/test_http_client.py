import unittest

import http_client


class HttpClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        await http_client.close_client()

    async def test_init_returns_async_client_and_is_idempotent(self):
        first = await http_client.init_client()
        second = await http_client.init_client()
        self.assertIs(first, second)
        self.assertIs(http_client.get_client(), first)

    async def test_get_client_before_init_raises(self):
        await http_client.close_client()
        with self.assertRaises(RuntimeError):
            http_client.get_client()

    async def test_close_is_safe_when_not_initialized(self):
        await http_client.close_client()
        await http_client.close_client()  # second call is a no-op
