"""Live spec-faithfulness audit of the real Verina benchmark over AXLE.

Each Verina task ships a postcondition plus a test suite where every input has a
correct ``expected`` output and several wrong ``unexpected`` outputs. That hands
us a rigorous, concrete faithfulness oracle with no mutant generation required:

  * **UNSOUND** (spec too strong)  ⇔ the postcondition *rejects* a correct output.
  * **INCOMPLETE** (spec too weak)  ⇔ the postcondition *accepts* a wrong output.

We test each witness by asking AXLE to ``check`` a one-line obligation
``<Name>_postcond <args> <value> (by native_decide) := by native_decide`` and
reading whether it proved, was evaluated false, or could not be decided. (We use
``native_decide`` purely to *evaluate* concrete decidable propositions — not to
discharge a real proof obligation — which is exactly how you stress a spec.)

The dataset (CC-BY-SA-4.0) is fetched on demand into a git-ignored cache via
``curl`` and is never vendored into this repo.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass, field

from ..core.audit import AuditReport
from ..core.oracle import OracleResult, Verdict

REPO_RAW = "https://raw.githubusercontent.com/sunblaze-ucb/verina/main/datasets/verina"
TREE_API = "https://api.github.com/repos/sunblaze-ucb/verina/git/trees/HEAD?recursive=1"
DEFAULT_CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".verina_cache")
PROOF_MARKER = "-- !benchmark @start proof_aux"


# --------------------------------------------------------------------------- #
# fetching (curl avoids framework-Python SSL issues; data stays git-ignored)
# --------------------------------------------------------------------------- #
def _curl(url: str) -> str:
    out = subprocess.run(["curl", "-sSL", url], capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"curl failed for {url}: {out.stderr[:200]}")
    return out.stdout


def list_task_ids(cache_dir: str = DEFAULT_CACHE) -> list[str]:
    """All 189 task ids, cached locally after the first call."""
    os.makedirs(cache_dir, exist_ok=True)
    cache = os.path.join(cache_dir, "task_ids.json")
    if os.path.exists(cache):
        return json.load(open(cache))
    tree = json.loads(_curl(TREE_API))
    ids = sorted({
        p.split("/")[2]
        for p in (e["path"] for e in tree["tree"])
        if p.startswith("datasets/verina/") and p.endswith("/task.lean")
    })
    json.dump(ids, open(cache, "w"))
    return ids


def fetch_task(task_id: str, cache_dir: str = DEFAULT_CACHE) -> str:
    """Download a task's files into the cache; return the task dir."""
    d = os.path.join(cache_dir, task_id)
    os.makedirs(d, exist_ok=True)
    for fname in ("task.lean", "task.json", "test.json"):
        path = os.path.join(d, fname)
        if not os.path.exists(path):
            open(path, "w").write(_curl(f"{REPO_RAW}/{task_id}/{fname}"))
    return d


# --------------------------------------------------------------------------- #
# task model
# --------------------------------------------------------------------------- #
@dataclass
class VerinaTask:
    id: str
    postcond_name: str       # "<Name>_postcond"
    params: list[str]        # parameter names, in signature order
    prelude: str             # task.lean up to the proof region (defs only, no sorry theorem)
    tests: list[dict] = field(default_factory=list)

    def probe(self, input_dict: dict, value) -> str:
        args = " ".join(f"({input_dict[p]})" for p in self.params)
        return (f"import Mathlib\n{self.prelude}\n"
                f"theorem faithfulness_probe : {self.postcond_name} {args} ({_lean(value)}) "
                f"(by native_decide) := by native_decide\n")


def _lean(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def load_task(task_id: str, cache_dir: str = DEFAULT_CACHE) -> VerinaTask:
    d = fetch_task(task_id, cache_dir)
    meta = json.load(open(os.path.join(d, "task.json")))
    tests = json.load(open(os.path.join(d, "test.json")))
    lean = open(os.path.join(d, "task.lean")).read()
    prelude = lean.split(PROOF_MARKER)[0]
    return VerinaTask(
        id=task_id,
        postcond_name=f"{meta['signature']['name']}_postcond",
        params=[p["param_name"] for p in meta["signature"]["parameters"]],
        prelude=prelude,
        tests=tests,
    )


# --------------------------------------------------------------------------- #
# verdict interpretation
# --------------------------------------------------------------------------- #
def _interpret(resp) -> str:
    """'holds' (postcond true), 'false' (postcond evaluated false), or 'inconclusive'."""
    if resp.okay:
        return "holds"
    errs = " ".join(getattr(resp.lean_messages, "errors", []) or []) or str(resp.lean_messages)
    if "evaluated that the proposition" in errs or "is false" in errs:
        return "false"
    return "inconclusive"


# --------------------------------------------------------------------------- #
# async audit (concurrent probes)
# --------------------------------------------------------------------------- #
async def _audit_async(tasks: list[VerinaTask], *, environment: str, concurrency: int,
                       max_tests: int, max_unexpected: int, timeout_s: float,
                       api_key=None, url=None, progress=False) -> AuditReport:
    import axle
    sem = asyncio.Semaphore(concurrency)

    async with axle.AxleClient(api_key=api_key, url=url, max_concurrency=concurrency) as client:
        async def run(content: str):
            async with sem:
                return await client.check(content=content, environment=environment,
                                          timeout_seconds=timeout_s)

        results: list[OracleResult] = []
        for task in tasks:
            probes = []   # (kind, input_dict, value, coro)
            for test in task.tests[:max_tests]:
                inp = test["input"]
                probes.append(("sound", inp, test["expected"], run(task.probe(inp, test["expected"]))))
                for w in test.get("unexpected", [])[:max_unexpected]:
                    probes.append(("comp", inp, w, run(task.probe(inp, w))))
            verdicts = await asyncio.gather(*[p[3] for p in probes], return_exceptions=True)

            sound, comp = [], []
            for (kind, inp, val, _), resp in zip(probes, verdicts):
                v = "inconclusive" if isinstance(resp, Exception) else _interpret(resp)
                (sound if kind == "sound" else comp).append((v, inp, val))

            res = _decide(task, sound, comp, n_probes=len(probes))
            results.append(res)
            if progress:
                print(res.one_line(), flush=True)

    return AuditReport(title="Live Verina spec-faithfulness audit (AXLE)",
                       oracle_name="verina-live", results=results)


def _decide(task: VerinaTask, sound, comp, n_probes: int) -> OracleResult:
    for v, inp, val in sound:
        if v == "false":
            return OracleResult(task.id, Verdict.UNSOUND,
                                "postcondition rejects a correct output (spec too strong)",
                                counterexample=f"correct output {val!r} rejected for input {inp}",
                                trials=n_probes, details={"check": "soundness"})
    for v, inp, val in comp:
        if v == "holds":
            return OracleResult(task.id, Verdict.INCOMPLETE,
                                "postcondition accepts a wrong output (spec too weak)",
                                counterexample=f"wrong output {val!r} accepted for input {inp}",
                                trials=n_probes, details={"check": "completeness"})
    decisive = (sound and comp
                and all(v == "holds" for v, _, _ in sound)
                and all(v == "false" for v, _, _ in comp))
    if decisive:
        return OracleResult(task.id, Verdict.FAITHFUL,
                            "correct outputs accepted; all wrong outputs rejected (on test witnesses)",
                            trials=n_probes, details={"check": "all"})
    return OracleResult(task.id, Verdict.INCONCLUSIVE,
                        "spec not decidable on some witnesses (no Decidable instance / timeout)",
                        trials=n_probes, details={"check": "inconclusive"})


def _run_async(coro):
    """Run a coroutine, working both standalone and inside a live loop (Jupyter)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)               # no running loop (CLI/script)
    import concurrent.futures                   # running loop: hand off to a worker thread
    with concurrent.futures.ThreadPoolExecutor(1) as ex:
        return ex.submit(asyncio.run, coro).result()


def run_live_audit(task_ids: list[str] | None = None, *, limit: int | None = None,
                   environment: str = "lean-4.28.0", concurrency: int = 8,
                   max_tests: int = 2, max_unexpected: int = 2, timeout_s: float = 200.0,
                   cache_dir: str = DEFAULT_CACHE, api_key=None, progress: bool = True) -> AuditReport:
    """Synchronous entry point: load tasks and run the live audit over AXLE."""
    ids = task_ids or list_task_ids(cache_dir)
    if limit is not None:
        ids = ids[:limit]
    tasks = [load_task(i, cache_dir) for i in ids]
    return _run_async(_audit_async(
        tasks, environment=environment, concurrency=concurrency, max_tests=max_tests,
        max_unexpected=max_unexpected, timeout_s=timeout_s, api_key=api_key, progress=progress,
    ))
