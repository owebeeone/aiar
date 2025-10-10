import io
import shutil
import tempfile
import unittest
from pathlib import Path

from aiar import (
    find_git_root,
    get_gitignore_spec,
    find_files_to_archive,
    create_aiar,
)


class AiarBaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="aiar_test_")
        self.root = Path(self.temp_dir)
        return super().setUp()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        return super().tearDown()

    def test_find_git_root_none_outside_repo(self):
        child = self.root / "sub" / "dir"
        child.mkdir(parents=True)
        self.assertIsNone(find_git_root(child))

    def test_find_git_root_detects_root(self):
        (self.root / ".git").mkdir()
        nested = self.root / "a" / "b"
        nested.mkdir(parents=True)
        self.assertEqual(find_git_root(nested), self.root.resolve())

    def test_get_gitignore_spec_disabled_returns_none(self):
        spec = get_gitignore_spec(self.root, use_gitignore=False)
        self.assertIsNone(spec)

    def test_get_gitignore_spec_matches_rules(self):
        # Create a mock git repo with .gitignore
        (self.root / ".git").mkdir()
        (self.root / ".gitignore").write_text("*.log\n!keep.log\n", encoding="utf-8")

        spec = get_gitignore_spec(self.root, use_gitignore=True)
        self.assertIsNotNone(spec)
        # Ignored
        self.assertTrue(spec.match_file("foo/bar/debug.log"))
        # Not ignored due to negation
        self.assertFalse(spec.match_file("keep.log"))

    def test_find_files_to_archive_respects_gitignore(self):
        # Setup repo
        (self.root / ".git").mkdir()
        (self.root / ".gitignore").write_text("*.tmp\n*.pyc\nnode_modules/\n", encoding="utf-8")

        base_dir = self.root
        # Create files
        included = [
            self.root / "src" / "main.py",
            self.root / "README.md",
        ]
        for p in included:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("ok", encoding="utf-8")

        ignored = [
            self.root / "build.tmp",
            self.root / "__pycache__" / "module.pyc",
            self.root / "node_modules" / "pkg" / "index.js",
        ]
        for p in ignored:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("ignored", encoding="utf-8")

        spec = get_gitignore_spec(base_dir, use_gitignore=True)
        files = set(find_files_to_archive([self.root], spec, base_dir))
        self.assertTrue(all(f.exists() for f in files))
        self.assertTrue((self.root / "src" / "main.py") in files)
        self.assertTrue((self.root / "README.md") in files)
        self.assertFalse((self.root / "build.tmp") in files)
        self.assertFalse((self.root / "__pycache__" / "module.pyc") in files)
        self.assertFalse((self.root / "node_modules" / "pkg" / "index.js") in files)

    def test_create_aiar_writes_header_and_files(self):
        base_dir = self.root
        f1 = self.root / "dir" / "a.txt"
        f2 = self.root / "b.txt"
        f1.parent.mkdir(parents=True, exist_ok=True)
        f1.write_text("content-a", encoding="utf-8")
        f2.write_text("content-b", encoding="utf-8")

        out = io.StringIO()
        create_aiar(out, {f1, f2}, base_dir)
        text = out.getvalue()

        # Header present
        self.assertIn("#!/bin/bash", text)
        self.assertIn("# --- DATA ---", text)
        # Separator base injected
        self.assertIn("++++++++++--------:", text)
        # Text file markers present
        self.assertIn(":t:dir/a.txt", text)
        self.assertIn(":t:b.txt", text)
        # File contents are included
        self.assertIn("content-a", text)
        self.assertIn("content-b", text)

    def test_create_aiar_handles_binary_files(self):
        base_dir = self.root
        binary_file = self.root / "data.bin"
        text_file = self.root / "readme.txt"
        
        # Create binary file with null bytes
        binary_file.write_bytes(b"\x00\x01\x02\xff\xfe")
        text_file.write_text("Hello\n", encoding="utf-8")

        out = io.StringIO()
        create_aiar(out, {binary_file, text_file}, base_dir)
        text = out.getvalue()

        # Binary file marker present
        self.assertIn(":b:data.bin", text)
        # Text file marker present
        self.assertIn(":t:readme.txt", text)
        # Text content preserved
        self.assertIn("Hello", text)
        # Base64 data present (binary file)
        # The base64 of b"\x00\x01\x02\xff\xfe" is "AAEC//4="
        self.assertIn("AAEC//4=", text)

    def test_create_aiar_binary_all_option(self):
        base_dir = self.root
        text_file = self.root / "test.txt"
        text_file.write_text("Plain text", encoding="utf-8")

        out = io.StringIO()
        create_aiar(out, {text_file}, base_dir, binary_all=True)
        text = out.getvalue()

        # With binary_all=True, text file should be marked as binary
        self.assertIn(":b:test.txt", text)
        # Should NOT have text marker
        self.assertNotIn(":t:test.txt", text)
        # Content should be base64-encoded
        # "Plain text" in base64 is "UGxhaW4gdGV4dA=="
        self.assertIn("UGxhaW4gdGV4dA==", text)

    def test_create_aiar_python_lang(self):
        base_dir = self.root
        text_file = self.root / "hello.txt"
        binary_file = self.root / "data.bin"
        
        text_file.write_text("Hello World\n", encoding="utf-8")
        binary_file.write_bytes(b"\x00\x01\x02\xff\xfe")

        out = io.StringIO()
        create_aiar(out, {text_file, binary_file}, base_dir, lang="py")
        text = out.getvalue()

        # Python shebang should NOT be present (Python doesn't use shebangs the same way)
        self.assertNotIn("#!/bin/bash", text)
        # Python imports should be present
        self.assertIn("import sys, os, re, base64", text)
        self.assertIn("from pathlib import Path", text)
        # Separator should be present
        self.assertIn("++++++++++--------:", text)
        # Python-style commented markers
        self.assertIn("# ++++++++++--------:", text)
        self.assertIn(":t:hello.txt", text)
        self.assertIn(":b:data.bin", text)
        # Content should be commented
        self.assertIn("# Hello World", text)
        # Base64 data should be commented
        self.assertIn("# AAEC//4=", text)

    def test_create_aiar_bare_lang(self):
        base_dir = self.root
        text_file = self.root / "hello.txt"
        binary_file = self.root / "data.bin"
        
        text_file.write_text("Hello World\n", encoding="utf-8")
        binary_file.write_bytes(b"\x00\x01\x02\xff\xfe")

        out = io.StringIO()
        create_aiar(out, {text_file, binary_file}, base_dir, lang="bare")
        text = out.getvalue()

        # Should NOT have bash script
        self.assertNotIn("#!/bin/bash", text)
        self.assertNotIn("handle_error", text)
        self.assertNotIn("extract_all", text)
        # Should have separator definition
        self.assertIn('SEPARATOR="++++++++++--------:', text)
        # Separator should be present in file markers
        self.assertIn("++++++++++--------:", text)
        self.assertIn(":t:hello.txt", text)
        self.assertIn(":b:data.bin", text)
        # Content should NOT be commented (plain text)
        self.assertIn("Hello World", text)
        self.assertNotIn("# Hello World", text)
        # Base64 data should NOT be commented
        self.assertIn("AAEC//4=", text)
        self.assertNotIn("# AAEC//4=", text)


if __name__ == "__main__":
    unittest.main()


