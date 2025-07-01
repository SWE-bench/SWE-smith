import ast
import os
import shutil
import tempfile
import unittest
from unittest.mock import Mock

from pathlib import Path
from swesmith.bug_gen.adapters.python import _build_entity
from swesmith.bug_gen import utils


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("""
def foo():
    return 1

class Bar:
    def baz(self):
        return 2
""")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_apply_code_change(self):
        # Setup CodeEntity and BugRewrite
        node = ast.parse(open(self.test_file).read()).body[0]
        entity = _build_entity(node, open(self.test_file).read(), self.test_file)
        bug = utils.BugRewrite(
            rewrite="def foo():\n    return 42\n",
            explanation="change return",
            strategy="test",
        )
        utils.apply_code_change(entity, bug)
        with open(self.test_file) as f:
            content = f.read()
        self.assertIn("return 42", content)

    def test_apply_patches(self):
        # Create a git repo and patch file
        repo = tempfile.mkdtemp()
        subprocess = __import__("subprocess")
        subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
        test_file = os.path.join(repo, "a.py")
        with open(test_file, "w") as f:
            f.write("print('hi')\n")
        for cmd in [
            "git branch -m main",
            "git add a.py",
            'git config user.email "you@example.com"',
            'git config user.name "Your Name"',
            "git commit --no-gpg-sign -m init",
        ]:
            subprocess.run(
                cmd.split(),
                cwd=repo,
                check=True,
                stdout=subprocess.DEVNULL,
            )
        with open(test_file, "w") as f:
            f.write("print('bye')\n")
        patch = utils.get_patch(repo)
        patch_file = os.path.join(self.test_dir, "patch.diff")
        print(patch)
        with open(patch_file, "w") as f:
            f.write(patch)
        # Reset rep o before applying patch
        subprocess.run(
            ["git", "reset", "--hard"], cwd=repo, check=True, stdout=subprocess.DEVNULL
        )
        subprocess.run(
            ["git", "clean", "-fd"], cwd=repo, check=True, stdout=subprocess.DEVNULL
        )
        # Apply the patch
        result = utils.apply_patches(repo, [patch_file])
        self.assertIsInstance(result, str)
        shutil.rmtree(repo)

    def test_extract_entities_from_directory(self):
        entities = utils.extract_entities_from_directory(
            self.test_dir, exclude_tests=False
        )
        self.assertTrue(any(e.src_code.startswith("def foo") for e in entities))
        self.assertTrue(any("class Bar" in e.src_code for e in entities))

    def test_get_bug_directory(self):
        mock_entity = Mock()
        mock_entity.name = "verify"
        mock_entity.signature = "public <T> T verify(T mock)"
        mock_entity.file_path = "some/file/path"
        bug_dir = utils.get_bug_directory(Path("some-log-dir"), mock_entity)
        self.assertEqual(Path("some-log-dir/some__file__path/verify_1ae25e6d"), bug_dir)

    def test_get_combos(self):
        items = [1, 2, 3]
        combos = utils.get_combos(items, 2, 2)
        self.assertEqual(len(combos), 2)
        self.assertTrue(all(len(c) >= 2 for c in combos))

    def test_get_entity_from_node(self):
        with open(self.test_file) as f:
            content = f.read()
        tree = ast.parse(content)
        node = tree.body[0]
        entity = _build_entity(node, content, self.test_file)
        self.assertEqual(entity.line_start, 2)
        self.assertIn("def foo", entity.src_code)

    def test_get_patch(self):
        repo = tempfile.mkdtemp()
        subprocess = __import__("subprocess")
        subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
        test_file = os.path.join(repo, "b.py")
        with open(test_file, "w") as f:
            f.write("print('hi')\n")
        for cmd in [
            "git add b.py",
            'git config user.email "you@example.com"',
            'git config user.name "Your Name"',
            "git commit --no-gpg-sign -m init",
        ]:
            subprocess.run(
                cmd.split(),
                cwd=repo,
                check=True,
                stdout=subprocess.DEVNULL,
            )
        with open(test_file, "w") as f:
            f.write("print('bye')\n")
        patch = utils.get_patch(repo)
        self.assertIsInstance(patch, str)
        shutil.rmtree(repo)


if __name__ == "__main__":
    unittest.main()
