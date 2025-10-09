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
        self.assertIn("# --- DATA PAYLOAD ---", text)
        # Separator injected
        self.assertIn("SEPARATOR=\"++++++++++--------:", text)
        # Paths appear after separator lines
        self.assertIn("a.txt", text)
        self.assertIn("b.txt", text)
        # File contents are included
        self.assertIn("content-a", text)
        self.assertIn("content-b", text)


if __name__ == "__main__":
    unittest.main()


