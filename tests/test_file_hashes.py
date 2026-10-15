import hashlib
import tempfile
import unittest
from pathlib import Path

from trading_primitives.file_hashes import sha256_file


class FileHashTests(unittest.TestCase):
    def test_published_empty_and_abc_digests(self):
        expected = {
            b"": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            b"abc": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        }
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"input.bin"
            for content, digest in expected.items():
                with self.subTest(content=content):
                    path.write_bytes(content)
                    self.assertEqual(sha256_file(path), digest)
                    self.assertEqual(path.read_bytes(), content)

    def test_streaming_crosses_chunk_boundary_and_preserves_bytes(self):
        content = bytes(range(256)) * 4097 + b"\r\n\0\xff"
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"input.bin"
            path.write_bytes(content)
            self.assertEqual(sha256_file(path), hashlib.sha256(content).hexdigest())
            self.assertEqual(path.read_bytes(), content)

    def test_missing_file_does_not_become_empty_digest(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                sha256_file(Path(d)/"missing")
