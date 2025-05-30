import ast
import os
import shutil
import tempfile
import unittest

from swesmith.bug_gen.adapters.python import py_get_entity_from_node
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
        entity = py_get_entity_from_node(
            node, open(self.test_file).read(), self.test_file
        )
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
            "git commit -m init",
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
        entity = py_get_entity_from_node(node, content, self.test_file)
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
            "git commit -m init",
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
