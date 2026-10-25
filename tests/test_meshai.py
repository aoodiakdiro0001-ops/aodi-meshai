"""Aodı-MeshAI — اختبارات بلا شبكة (الموجه، الصندوق، التخزين)."""
import sys, unittest
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent / "core"
sys.path.insert(0, str(CORE))

import router          # noqa: E402
import sandbox         # noqa: E402


class RouterTests(unittest.TestCase):
    def test_easy_short(self):
        self.assertEqual(router.classify("اكتب دالة تجمع قائمة أعداد")["tier"], "easy")

    def test_hard_async_and_pipeline(self):
        t = router.classify("نظام مؤلف من مهام async متوازية مع redis cache و parser معقد")
        self.assertEqual(t["tier"], "hard")

    def test_medium(self):
        t = router.classify("دالة تقرأ json وتحقق من وجود مفتاح")
        self.assertIn(t["tier"], ("medium", "easy"))

    def test_pick_nodes_by_tag(self):
        nodes = [{"name": "s", "tags": ["small"]},
                 {"name": "b", "tags": ["strong"]}]
        self.assertEqual(router.pick_nodes(nodes, "hard")[0]["name"], "b")
        self.assertEqual(router.pick_nodes(nodes, "easy")[0]["name"], "s")


class SandboxTests(unittest.TestCase):
    def test_fail_exit(self):
        r = sandbox.run_code("raise ValueError('boom')\n", timeout=5)
        self.assertFalse(r["ok"])
        self.assertIn("boom", r["output"])

    def test_infinite_loop_killed(self):
        r = sandbox.run_code("while True:\n    x = 1\n", timeout=3)
        self.assertFalse(r["ok"])
        self.assertNotEqual(r["exit_code"], 0)

    def test_memory_cap(self):
        code = "x = [0] * (10**11)\n"
        r = sandbox.run_code(code, mem_mb=128, timeout=4)
        self.assertFalse(r["ok"])   # يجب أن يُقتل بالحدود

    def test_harness_passes(self):
        r = sandbox.run_code("def f(xs): return sum(xs)\n",
                             "assert f([1,2,3]) == 6\n", timeout=5)
        self.assertTrue(r["ok"], r.get("output"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
