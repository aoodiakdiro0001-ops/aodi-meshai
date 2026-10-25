"""Aodı-MeshAI — sandbox executor: عزل عبر -I + rlimits + kill group عند المهلة."""
import os, resource, subprocess, sys, tempfile, time, signal

import config


def _limits(mem_mb):
    def apply():
        mem = mem_mb * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
        except Exception:
            pass
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (config.SANDBOX_TIMEOUT,
                                                     config.SANDBOX_TIMEOUT + 2))
        except Exception:
            pass
        try:
            resource.setrlimit(resource.RLIMIT_NPROC, (24, 24))
        except Exception:
            pass
        try:
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))  # لا coredumps
        except Exception:
            pass
    return apply


def run_code(code, test_harness="", timeout=None, mem_mb=None):
    """يكتب code مرة + harness ثانياً إذا أُمر، فيثبت إن دخل نجاح فحص الثغرة."""
    timeout = timeout or config.SANDBOX_TIMEOUT
    mem_mb = mem_mb or config.SANDBOX_MEM_MB
    with tempfile.TemporaryDirectory(prefix="mhx_sbx_") as d:
        src = os.path.join(d, "app.py")
        body = code + ("\n\n# --- harness ---\n" + test_harness if test_harness else "")
        with open(src, "w", encoding="utf-8") as f:
            f.write(body)
        t0 = time.time()
        try:
            proc = subprocess.Popen(
                [sys.executable, "-I", src], cwd=d,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                preexec_fn=_limits(mem_mb), start_new_session=True)
            out, _ = proc.communicate(timeout=timeout)
            dur = int((time.time() - t0) * 1000)
            txt = out.decode("utf-8", "replace")[-3000:]
            return {"ok": proc.returncode == 0, "exit_code": proc.returncode,
                    "output": txt, "duration_ms": dur,
                    "error": None if proc.returncode == 0 else txt[-800:]}
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                pass
            return {"ok": False, "exit_code": -1,
                    "output": "", "duration_ms": int((time.time() - t0) * 1000),
                    "error": f"timeout: تجاوز {timeout} ثانية (قتل جماعي)"}
