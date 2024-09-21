import json

import tornado

from app import make_app


class TestApp(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        return make_app()

    def test_request(self):
        for path, options, status_code, payload in [
            # REQUEST: tuple = (path: str, options: dict, status_code: int, payload),
            ("/foo", {"method": "GET"}, 204, None),
            ("/bar", {"method": "GET"}, 204, None),
            ("/ping", {"method": "GET"}, 200, {"ping": "pong"}),
            ("/any/path/ending/in/help", {"method": "GET"}, 200, None),
            (
                "/address",
                {
                    "method": "GET",
                    "headers": {
                        "X-Forwarded-For": "4.3.2.1",
                    },
                },
                200,
                "4.3.2.1",
            ),
            (
                "/address?compact",
                {
                    "method": "GET",
                    "headers": {
                        "X-Forwarded-For": "4.3.2.1",
                    },
                },
                200,
                "4.3.2.1",
            ),
            ("/address/4.3.2.1", {"method": "GET"}, 200, "4.3.2.1"),
            ("/address/4.3.2.1?compact", {"method": "GET"}, 200, "4.3.2.1"),
            ("/address/2600::1", {"method": "GET"}, 200, "2600::1"),
        ]:
            print(f"path: {path!r}, options: {options!r}, status_code: {status_code}")
            # Make the HTTP request
            response = self.fetch(f"{path}", **options)
            # Check response code for the expected value
            self.assertEqual(response.code, status_code)
            # Check response body for expected values
            if status_code == 200 and payload is not None:
                response_body = json.loads(response.body)
                if response_body.get("address", False):
                    print(
                        f"address: {response_body.get('address')!r}, expected: {payload!r}"
                    )
                    self.assertEqual(response_body["address"], payload)
                else:
                    print(f"body: {response_body!r}, expected: {payload!r}")
                    self.assertEqual(response_body, payload)
