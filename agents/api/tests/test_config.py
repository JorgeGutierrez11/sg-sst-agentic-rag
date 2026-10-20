import os
import unittest
from unittest.mock import patch

from agents.api.config import get_cors_allowed_origins


class CorsAllowedOriginsTests(unittest.TestCase):
    def test_parses_comma_separated_origins(self) -> None:
        with patch.dict(
            os.environ,
            {"CORS_ALLOWED_ORIGINS": " http://localhost:3000 , https://app.example.com "},
        ):
            origins = get_cors_allowed_origins()

        self.assertEqual(origins, ["http://localhost:3000", "https://app.example.com"])

    def test_rejects_missing_variable(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "CORS_ALLOWED_ORIGINS"):
                get_cors_allowed_origins()

    def test_rejects_wildcard_origin(self) -> None:
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "*"}):
            with self.assertRaisesRegex(ValueError, "CORS_ALLOWED_ORIGINS"):
                get_cors_allowed_origins()

    def test_rejects_malformed_origin(self) -> None:
        for value in ("localhost:3000", "ftp://example.com", "http://example.com/", "http://example.com/app"):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": value}):
                    with self.assertRaisesRegex(ValueError, "CORS_ALLOWED_ORIGINS"):
                        get_cors_allowed_origins()


if __name__ == "__main__":
    unittest.main()
