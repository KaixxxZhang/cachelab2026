#!/usr/bin/env python3
"""Part B GEMM analysis: reproduce official misses and sweep register tiles.

The cache model matches the lab: s=5, E=1, b=4, direct-mapped, write-allocate.
Simulated addresses start at 0x30000000 with A, B, C, buffer packed in that order.
The blocked kernel uses the same access order as gemm_ref.cpp:

    for i0 step R:
        for j0 step S:
            for k in 0..n-1:
                load A[i0:i0+Rh, k]   # Rh = min(R, m-i0)
                load B[k, j0:j0+Sh]
            store C[i0:i0+Rh, j0:j0+Sh] row-major

Run from the repository root:

    python3 manual/scripts/analyze_partb.py
    python3 manual/scripts/analyze_partb.py --crosscheck

--crosscheck compiles a few non-student tiles with the real framework and
compares their traces to this simulator. It copies the repo to /tmp and does
not modify the working tree.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DATA = ROOT / "manual" / "data"
OUT_GEN = ROOT / "manual" / "generated"
BASE = 0x30000000
SETS = 32
BLOCK_INTS = 4  # b=4 -> 16 bytes -> 4 ints

CASES = {
    "case0": (2, 2, 2),
    "case1": (16, 16, 16),
    "case2": (32, 32, 32),
    "case3": (27, 41, 27),
}
STUDENT = {"case1": (4, 4), "case2": (4, 4), "case3": (4, 6)}
BASELINE_LAT = {}  # filled after baseline simulation


def addr_of(int_index: int) -> int:
    return BASE + 4 * int_index


def block_id(int_index: int) -> int:
    return int_index >> 2


def set_of_index(int_index: int) -> int:
    # base is 512-byte aligned, so the set depends only on the int index.
    return block_id(int_index) & 31


def tag_of_index(int_index: int) -> int:
    return (BASE >> 9) + (int_index >> 7)


class Cache:
    def __init__(self):
        self.slots = [None] * SETS  # (block, meta) or None
        self.seen = set()
        self.miss = 0
        self.hit = 0

    def access(self, int_index: int):
        blk = block_id(int_index)
        s = blk & 31
        prev = self.slots[s]
        cold = blk not in self.seen
        hit = prev is not None and prev[0] == blk
        evicted = None
        if hit:
            self.hit += 1
        else:
            self.miss += 1
            if prev is not None:
                evicted = prev
            self.slots[s] = (blk, None)
        self.seen.add(blk)
        return {
            "hit": hit,
            "cold": cold and not hit,
            "conflict": (not hit) and (not cold),
            "set": s,
            "block": blk,
            "evicted": None if evicted is None else evicted[0],
        }


def layout(m, n, p):
    a_n, b_n, c_n = m * n, n * p, m * p
    b_base, c_base = a_n, a_n + b_n
    buf = c_base + c_n
    def info(name, start, count):
        if count == 0:
            return {}
        first = start
        last = start + count - 1
        return {
            "name": name,
            "ints": count,
            "bytes": count * 4,
            "start_int": start,
            "end_int_inclusive": last,
            "start_addr": hex(addr_of(start)),
            "end_addr_inclusive": hex(addr_of(last) + 3),
            "start_mod_512B": (start * 4) % 512,
            "start_align_mod4": start % 4,
            "start_set": set_of_index(start),
            "start_block": block_id(start),
            "blocks_touched": block_id(last) - block_id(first) + 1,
        }
    return {
        "A": info("A", 0, a_n),
        "B": info("B", b_base, b_n),
        "C": info("C", c_base, c_n),
        "buffer": info("buffer", buf, 64),
        "shared_blocks": shared_blocks(a_n, b_n, c_n),
    }


def shared_blocks(a_n, b_n, c_n):
    """Blocks that contain elements of two matrices, with the elements named."""
    b_base = a_n
    c_base = a_n + b_n
    ranges = [("A", 0, a_n), ("B", b_base, b_n), ("C", c_base, c_n)]
    by_block = defaultdict(list)
    for name, start, count in ranges:
        if count == 0:
            continue
        for t in range(start, start + count):
            by_block[block_id(t)].append((name, t - start))
    shared = []
    for blk, items in by_block.items():
        mats = {it[0] for it in items}
        if len(mats) > 1:
            shared.append({
                "block": blk,
                "set": blk & 31,
                "elements": [
                    {"matrix": name, "local_index": local, "global_index": None}
                    for name, local in items
                ],
            })
    # fill global and coordinates later by caller if needed
    return shared


def iter_tiles(m, p, R, S):
    for i0 in range(0, m, R):
        rh = min(R, m - i0)
        for j0 in range(0, p, S):
            sh = min(S, p - j0)
            yield i0, j0, rh, sh


def miss_reg_formula(m, n, p, R, S):
    """Exact instruction count for the blocked kernel, edges included.

    Each i-tile of height Rh is paired with every j-tile, so
        sum Rh = m * ceil(p / S)
        sum Sh = p * ceil(m / R)
        sum Rh*Sh = m * p
    and each tile issues n*(Rh+Sh) loads and Rh*Sh stores.
    """
    return n * (m * ceil_div(p, S) + p * ceil_div(m, R)) + m * p


def ceil_div(a, b):
    return (a + b - 1) // b


def regs_for(R, S):
    """Peak live regs: 4 ptr + i0 + j0 + k + R*S acc + R A-regs + 1 reused b."""
    return R * S + R + 8


def legal(R, S, m, p):
    return 1 <= R <= m and 1 <= S <= p and regs_for(R, S) <= 36


def simulate(m, n, p, R, S, order="A_then_B", loop="ij", record_tiles=None):
    """Simulate one kernel. record_tiles is a set of (i0, j0) or None."""
    b_base = m * n
    c_base = b_base + n * p
    cache = Cache()
    stats = {mat: Counter() for mat in "ABC"}
    a_cat = Counter()
    # block -> (i0, j0) of the last A access that touched it
    a_last = {}
    timeline = []
    b_slice_lines = 0
    c_store_lines = 0
    b_temporal_hit = 0
    c_temporal_hit = 0
    per_tile = {}
    tile_list = list(iter_tiles(m, p, R, S))
    if loop == "ji":
        # same tiles, j outer
        tile_list.sort(key=lambda t: (t[1], t[0]))
    elif loop != "ij":
        raise ValueError(loop)

    def touch(mat, index, meta):
        nonlocal b_temporal_hit, c_temporal_hit
        res = cache.access(index)
        st = stats[mat]
        st["acc"] += 1
        if res["hit"]:
            st["hit"] += 1
            if mat == "B" and not meta.get("first_in_slice_line", True):
                st["spatial_hit"] += 1
            elif mat == "C" and not meta.get("first_in_store_line", True):
                st["spatial_hit"] += 1
            elif mat == "B":
                b_temporal_hit += 1
                st["temporal_hit"] += 1
            elif mat == "C":
                c_temporal_hit += 1
                st["temporal_hit"] += 1
            else:
                st["temporal_hit"] += 1
        else:
            st["miss"] += 1
            if res["cold"]:
                st["cold"] += 1
            else:
                st["conflict"] += 1
        return res

    for i0, j0, rh, sh in tile_list:
        tile_key = (i0, j0, rh, sh)
        tile_stat = Counter()
        per_tile[tile_key] = tile_stat
        want = record_tiles is not None and (i0, j0) in record_tiles
        for k in range(n):
            a_items = [("A", (i0 + r) * n + k, {"i": i0 + r, "k": k, "r": r}) for r in range(rh)]
            b_items = []
            seen_lines = set()
            for s in range(sh):
                index = b_base + k * p + (j0 + s)
                first = block_id(index) not in seen_lines
                seen_lines.add(block_id(index))
                b_items.append(("B", index, {"k": k, "j": j0 + s, "first_in_slice_line": first}))
            b_slice_lines += len(seen_lines)
            seq = a_items + b_items if order == "A_then_B" else b_items + a_items
            if order not in ("A_then_B", "B_then_A"):
                raise ValueError(order)
            step_rec = []
            for mat, index, meta in seq:
                res = touch(mat, index, meta)
                if mat == "A":
                    blk = res["block"]
                    if res["hit"]:
                        cat = "hit"
                    elif res["cold"]:
                        cat = "cold"
                    else:
                        prev = a_last.get(blk)
                        if prev is None:
                            cat = "other"  # first A touch, but B/C already used the block
                        elif prev[0] == i0 and prev[1] == j0:
                            cat = "intra"
                        elif prev[0] == i0:
                            cat = "cross_j"
                        else:
                            cat = "cross_i"
                    if not res["hit"]:
                        a_cat[cat] += 1
                        tile_stat[cat] += 1
                    a_last[blk] = (i0, j0)
                    if want:
                        step_rec.append((mat, meta.get("r"), res["hit"], res["set"], res["evicted"]))
                elif want and mat == "B":
                    step_rec.append((mat, meta["j"], res["hit"], res["set"], res["evicted"]))
            if want:
                timeline.append({"i0": i0, "j0": j0, "k": k, "rh": rh, "sh": sh, "steps": step_rec})
        seen_c = set()
        for r in range(rh):
            for s in range(sh):
                index = c_base + (i0 + r) * p + (j0 + s)
                first = block_id(index) not in seen_c
                seen_c.add(block_id(index))
                touch("C", index, {"i": i0 + r, "j": j0 + s, "first_in_store_line": first})
        c_store_lines += len(seen_c)
        tile_stat["c_lines"] = len(seen_c)

    miss_reg = sum(stats[m_]["acc"] for m_ in "ABC")
    formula = miss_reg_formula(m, n, p, R, S)
    if miss_reg != formula:
        raise RuntimeError(f"miss_reg {miss_reg} != formula {formula} for {R}x{S}")
    return {
        "miss_reg": miss_reg,
        "miss_cache": cache.miss,
        "hits": cache.hit,
        "unique_blocks": len(cache.seen),
        "latency": 15 * cache.miss + miss_reg,
        "stats": {m_: dict(stats[m_]) for m_ in "ABC"},
        "a_cat": dict(a_cat),
        "b_slice_lines": b_slice_lines,
        "c_store_lines": c_store_lines,
        "b_temporal_hit": b_temporal_hit,
        "c_temporal_hit": c_temporal_hit,
        "per_tile": {f"{i0},{j0},{rh},{sh}": dict(st) for (i0, j0, rh, sh), st in per_tile.items()},
        "timeline": timeline,
        "n_tiles": len(tile_list),
    }


def simulate_baseline(m, n, p):
    return simulate(m, n, p, 1, 1)


def simulate_kblock_spill(m, n, p, R, S, kc):
    """k-blocking outside j, spilling C once per (tile, k-chunk).

    Accesses per chunk: Rh loads of A and Sh loads of B for each k, plus a
    store of the Rh*Sh accumulators. Later chunks also reload C. This is NOT
    the student's kernel; it is an improvement candidate.
    """
    b_base = m * n
    c_base = b_base + n * p
    cache = Cache()
    acc = 0
    misses = 0

    def touch(index):
        nonlocal acc, misses
        acc += 1
        if not cache.access(index)["hit"]:
            misses += 1

    chunks = list(range(0, n, kc))
    for i0, j0, rh, sh in iter_tiles(m, p, R, S):
        for ci, kk in enumerate(chunks):
            if ci > 0:
                for r in range(rh):
                    for s in range(sh):
                        touch(c_base + (i0 + r) * p + (j0 + s))
            for k in range(kk, min(n, kk + kc)):
                for r in range(rh):
                    touch((i0 + r) * n + k)
                for s in range(sh):
                    touch(b_base + k * p + (j0 + s))
            for r in range(rh):
                for s in range(sh):
                    touch(c_base + (i0 + r) * p + (j0 + s))
    return {"miss_reg": acc, "miss_cache": misses, "latency": 15 * misses + acc, "kc": kc}


def load_trace(path: Path):
    ops = []
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        op = parts[0]
        addr = int(parts[1].split(",")[0], 16)
        ops.append((op, addr))
    return ops


def kernel_trace(m, n, p, R, S):
    b_base = m * n
    c_base = b_base + n * p
    ops = []
    for i0, j0, rh, sh in iter_tiles(m, p, R, S):
        for k in range(n):
            for r in range(rh):
                ops.append(("L", addr_of((i0 + r) * n + k)))
            for s in range(sh):
                ops.append(("L", addr_of(b_base + k * p + (j0 + s))))
        for r in range(rh):
            for s in range(sh):
                ops.append(("S", addr_of(c_base + (i0 + r) * p + (j0 + s))))
    return ops


def compare_official_traces():
    report = {}
    for case, (m, n, p) in CASES.items():
        R, S = (1, 1) if case == "case0" else STUDENT[case]
        pred = kernel_trace(m, n, p, R, S)
        for kind, name in (("impl", case), ("base", f"{case}_baseline")):
            path = ROOT / "gemm_traces" / f"{name}.trace"
            if not path.exists():
                report[name] = "missing"
                continue
            got = load_trace(path)
            # baseline is the 1x1 kernel; impl for case0 is also 1x1
            expect = kernel_trace(m, n, p, 1, 1) if kind == "base" or case == "case0" else pred
            report[name] = {
                "match": got == expect,
                "n_got": len(got),
                "n_expect": len(expect),
                "first_mismatch": next((i for i, (a, b) in enumerate(zip(got, expect)) if a != b), None)
                if len(got) == len(expect) else "len",
            }
    return report


def sweep_case(case):
    m, n, p = CASES[case]
    rows = []
    for R in range(1, m + 1):
        for S in range(1, p + 1):
            if not legal(R, S, m, p):
                continue
            sim = simulate(m, n, p, R, S)
            base_lat = BASELINE_LAT[case]
            rows.append({
                "R": R,
                "S": S,
                "regs": regs_for(R, S),
                "div_m": m % R == 0,
                "div_p": p % S == 0,
                "divisible": m % R == 0 and p % S == 0,
                "miss_reg": sim["miss_reg"],
                "miss_cache": sim["miss_cache"],
                "latency": sim["latency"],
                "speedup": base_lat / sim["latency"],
                "A_miss": sim["stats"]["A"]["miss"],
                "B_miss": sim["stats"]["B"]["miss"],
                "C_miss": sim["stats"]["C"]["miss"],
                "A_cold": sim["stats"]["A"]["cold"],
                "B_cold": sim["stats"]["B"]["cold"],
                "C_cold": sim["stats"]["C"]["cold"],
                "A_acc": sim["stats"]["A"]["acc"],
                "B_acc": sim["stats"]["B"]["acc"],
                "C_acc": sim["stats"]["C"]["acc"],
                "a_cat": sim["a_cat"],
                "b_slice_lines": sim["b_slice_lines"],
                "c_store_lines": sim["c_store_lines"],
                "b_temporal_hit": sim["b_temporal_hit"],
                "c_temporal_hit": sim["c_temporal_hit"],
                "B_spatial_hit": sim["stats"]["B"].get("spatial_hit", 0),
                "C_spatial_hit": sim["stats"]["C"].get("spatial_hit", 0),
                "n_tiles": sim["n_tiles"],
                "factor": (sim["miss_reg"] - m * p) / (m * n * p),
            })
    rows.sort(key=lambda r: (r["latency"], r["miss_reg"], r["R"], r["S"]))
    return rows


def tile_pattern(sim):
    """Summarize per-tile A-miss categories. Values are sorted unique counts."""
    groups = defaultdict(list)
    for key, st in sim["per_tile"].items():
        i0, j0, rh, sh = key.split(",")
        groups[f"{rh}x{sh}"].append({
            "i0": int(i0),
            "j0": int(j0),
            "cold": st.get("cold", 0),
            "intra": st.get("intra", 0),
            "cross_j": st.get("cross_j", 0),
            "cross_i": st.get("cross_i", 0),
            "other": st.get("other", 0),
            "c_lines": st.get("c_lines", 0),
        })
    summary = {}
    for shape, tiles in groups.items():
        def uniq(field):
            return sorted({t[field] for t in tiles})
        # split first j of each i vs the rest, when several j exist
        j0s = sorted({t["j0"] for t in tiles})
        first_j = j0s[0]
        summary[shape] = {
            "n_tiles": len(tiles),
            "cold": uniq("cold"),
            "intra": uniq("intra"),
            "cross_j": uniq("cross_j"),
            "cross_i": uniq("cross_i"),
            "other": uniq("other"),
            "first_j_cross": sorted({t["cross_j"] for t in tiles if t["j0"] == first_j}),
            "later_j_cross": sorted({t["cross_j"] for t in tiles if t["j0"] != first_j}),
            "first_j_cold": sorted({t["cold"] for t in tiles if t["j0"] == first_j}),
            "later_j_cold": sorted({t["cold"] for t in tiles if t["j0"] != first_j}),
            "tiles": tiles,
        }
    return summary


def variants(case, R, S):
    m, n, p = CASES[case]
    out = {}
    for order in ("A_then_B", "B_then_A"):
        for loop in ("ij", "ji"):
            if order == "A_then_B" and loop == "ij":
                continue  # already the main result
            sim = simulate(m, n, p, R, S, order=order, loop=loop)
            out[f"{loop}/{order}"] = {
                "miss_cache": sim["miss_cache"],
                "miss_reg": sim["miss_reg"],
                "latency": sim["latency"],
                "A_miss": sim["stats"]["A"]["miss"],
                "B_miss": sim["stats"]["B"]["miss"],
                "C_miss": sim["stats"]["C"]["miss"],
            }
    kc_list = [k for k in (4, 8, 16, n) if 1 < k < n]
    out["kblock_spill"] = []
    for kc in kc_list:
        sim = simulate_kblock_spill(m, n, p, R, S, kc)
        sim["speedup_vs_student_kernel_latency_only"] = None
        out["kblock_spill"].append(sim)
    return out


def describe_shared(m, n, p):
    lay = layout(m, n, p)
    a_n, b_n = m * n, n * p
    b_base, c_base = a_n, a_n + b_n
    described = []
    for item in lay["shared_blocks"]:
        elems = []
        for el in item["elements"]:
            name, local = el["matrix"], el["local_index"]
            if name == "A":
                i, j = divmod(local, n)
                coord = f"A[{i}][{j}]"
                g = local
            elif name == "B":
                i, j = divmod(local, p)
                coord = f"B[{i}][{j}]"
                g = b_base + local
            else:
                i, j = divmod(local, p)
                coord = f"C[{i}][{j}]"
                g = c_base + local
            elems.append({"coord": coord, "global": g, "matrix": name})
        described.append({"block": item["block"], "set": item["set"], "elements": elems})
    lay["shared_blocks"] = described
    return lay


def fmt_tex_int(n):
    return f"{n:,}".replace(",", "{,}")


def speedup_tex(x):
    return f"{x:.4f}"


def write_sweep_tex(case, rows, student):
    m, n, p = CASES[case]
    lines = []
    lines.append("% auto-generated by analyze_partb.py — do not edit")
    lines.append("\\begin{longtable}{@{}rrrrrrrrrrr@{}}")
    lines.append(
        "\\caption{" + case
        + f"（${m}\\times {n}\\times {p}$）全部满足 $RS+R+8\\le 36$ 的 $R\\times S$，"
        + "按 latency 从小到大。加粗行是实现采用的块形。"
        + f"「整除」表示 $R\\mid {m}$ 且 $S\\mid {p}$。"
        + "A、B、C 三列是各自的 cache 缺失次数。}"
    )
    lines.append("\\label{tab:sweep-" + case + "}\\\\")
    header = (
        "\\toprule $R$ & $S$ & 寄存器 & 整除 & $miss_{reg}$ & $miss_{cache}$ & "
        "A & B & C & latency & 加速比\\\\\\midrule\\endfirsthead"
    )
    lines.append(header)
    lines.append("\\toprule $R$ & $S$ & 寄存器 & 整除 & $miss_{reg}$ & $miss_{cache}$ & "
                 "A & B & C & latency & 加速比\\\\\\midrule\\endhead")
    lines.append("\\bottomrule\\endfoot")
    for r in rows:
        div = "是" if r["divisible"] else "否"
        mark_r = r["R"]
        mark_s = r["S"]
        rs = f"{mark_r} & {mark_s}"
        if (r["R"], r["S"]) == student:
            rs = f"\\textbf{{{mark_r}}} & \\textbf{{{mark_s}}}"
            div = f"\\textbf{{{div}}}"
        lines.append(
            f"{rs} & {r['regs']} & {div} & {r['miss_reg']} & {r['miss_cache']} & "
            f"{r['A_miss']} & {r['B_miss']} & {r['C_miss']} & {r['latency']} & {r['speedup']:.4f}\\\\"
        )
    lines.append("\\end{longtable}")
    (OUT_GEN / f"sweep_{case}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_top_tex(case, rows, student, k=12):
    """Short table: student row, best divisible, best overall, and a few neighbors."""
    chosen = []
    seen = set()

    def add(r, note):
        key = (r["R"], r["S"])
        if key in seen:
            return
        seen.add(key)
        chosen.append((r, note))

    add(rows[0], "latency 最小")
    div = [r for r in rows if r["divisible"]]
    if div:
        add(div[0], "整除块里 latency 最小")
    for r in rows:
        if (r["R"], r["S"]) == student:
            add(r, "实现所采用")
            break
    # also the best few by latency
    for r in rows[:k]:
        add(r, "")
    # and every divisible shape, they are few and pedagogically useful
    for r in rows:
        if r["divisible"]:
            add(r, "两边整除")
    lines = []
    lines.append("% auto-generated")
    lines.append("\\begin{tabular}{@{}rrrrrrrrl@{}}")
    lines.append("\\toprule $R\\times S$ & 寄存器 & 整除 & $miss_{reg}$ & $miss_c$ & A/B/C miss & latency & 加速比 & 备注\\\\")
    lines.append("\\midrule")
    for r, note in chosen:
        div = "是" if r["divisible"] else "否"
        star = note
        if (r["R"], r["S"]) == student and "实现" not in star:
            star = (star + "；实现所采用").strip("；")
        lines.append(
            f"${r['R']}\\times{r['S']}$ & {r['regs']} & {div} & {r['miss_reg']} & {r['miss_cache']} & "
            f"{r['A_miss']}/{r['B_miss']}/{r['C_miss']} & {r['latency']} & {r['speedup']:.4f} & {star}\\\\"
        )
    lines.append("\\bottomrule\\end{tabular}")
    (OUT_GEN / f"top_{case}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_timeline_tex(case, sim, limit_k=8):
    """Compact hit/miss timeline for recorded tiles."""
    if not sim["timeline"]:
        return
    by = defaultdict(list)
    for step in sim["timeline"]:
        by[(step["i0"], step["j0"])].append(step)
    parts = []
    for (i0, j0), steps in by.items():
        rh = steps[0]["rh"]
        parts.append(f"% tile i0={i0} j0={j0}")
        parts.append("\\begin{tabular}{@{}r" + "c" * rh + "cl@{}}")
        ahead = " & ".join([f"A$_{{{r}}}$" for r in range(rh)])
        parts.append(f"\\toprule $k$ & {ahead} & B 切片 & 说明\\\\")
        parts.append("\\midrule")
        for step in steps:
            if step["k"] >= limit_k and not (case == "case2" and step["k"] in (0, 1, 2, 3, 4)):
                if step["k"] > limit_k:
                    continue
            a_cells = []
            b_miss = 0
            b_hit = 0
            notes = []
            for mat, idx, hit, s, ev in step["steps"]:
                if mat == "A":
                    a_cells.append("命中" if hit else "缺失")
                    if not hit and ev is not None:
                        notes.append(f"A{idx}挤出行{ev}")
                else:
                    if hit:
                        b_hit += 1
                    else:
                        b_miss += 1
            # only keep a short note: count of A misses
            nmiss = sum(1 for c in a_cells if c == "缺失")
            note = f"{nmiss} 次 A 缺失" if nmiss else "A 全命中"
            parts.append(
                f"{step['k']} & " + " & ".join(a_cells) + f" & {b_miss} 缺失/{b_hit} 命中 & {note}\\\\"
            )
        parts.append("\\bottomrule\\end{tabular}")
    (OUT_GEN / f"timeline_{case}.tex").write_text("\n".join(parts) + "\n", encoding="utf-8")


def emit_kernel_cpp(case, R, S):
    m, n, p = CASES[case]
    rem_m, rem_p = m % R, p % S

    def body(rh, sh, j_expr):
        acc = []
        for r in range(rh):
            names = ", ".join([f"c{r}{s} = 0" for s in range(sh)])
            acc.append(f"      reg {names};")
        loads_a = "\n".join(
            [f"        reg a{r} = A[(i0 + {r}) * n + k];" for r in range(rh)]
        )
        bloads = []
        for s in range(sh):
            bloads.append(f"        b = B[k * p + ({j_expr} + {s})];")
            uses = " ".join([f"c{r}{s} += a{r} * b;" for r in range(rh)])
            bloads.append(f"        {uses}")
        stores = []
        for r in range(rh):
            for s in range(sh):
                stores.append(
                    f"      C[(i0 + {r}) * p + ({j_expr} + {s})] = c{r}{s};"
                )
        return "\n".join(acc + [
            "      for (reg k = 0; k < n; k = k + 1) {",
            loads_a,
            "        reg b = B[k * p + (" + j_expr + " + 0)];",
            "        " + " ".join([f"c{r}0 += a{r} * b;" for r in range(rh)]),
            *bloads[2:],  # s=0 already emitted
            "      }",
            *stores,
        ])

    # The s=0 path is duplicated if I prepend b and also slice bloads. Let me rebuild cleanly.
    def body(rh, sh, j_expr):
        lines = []
        for r in range(rh):
            names = ", ".join([f"c{r}{s} = 0" for s in range(sh)])
            lines.append(f"      reg {names};")
        lines.append("      for (reg k = 0; k < n; k = k + 1) {")
        for r in range(rh):
            lines.append(f"        reg a{r} = A[(i0 + {r}) * n + k];")
        lines.append(f"        reg b = B[k * p + ({j_expr} + 0)];")
        lines.append("        " + " ".join(f"c{r}0 += a{r} * b;" for r in range(rh)))
        for s in range(1, sh):
            lines.append(f"        b = B[k * p + ({j_expr} + {s})];")
            lines.append("        " + " ".join(f"c{r}{s} += a{r} * b;" for r in range(rh)))
        lines.append("      }")
        for r in range(rh):
            for s in range(sh):
                lines.append(f"      C[(i0 + {r}) * p + ({j_expr} + {s})] = c{r}{s};")
        return "\n".join(lines)

    chunks = []
    full_i_cond = f"i0 + {R - 1} < m"
    full_j_cond = f"j0 + {S - 1} < p"
    chunks.append(f"  for (reg i0 = 0; {full_i_cond}; i0 = i0 + {R}) {{")
    chunks.append(f"    for (reg j0 = 0; {full_j_cond}; j0 = j0 + {S}) {{")
    chunks.append(body(R, S, "j0"))
    chunks.append("    }")
    if rem_p:
        chunks.append(f"    for (reg j0 = p - {rem_p}; j0 + {rem_p - 1} < p; j0 = j0 + {rem_p}) {{")
        chunks.append(body(R, rem_p, "j0"))
        chunks.append("    }")
    chunks.append("  }")
    if rem_m:
        chunks.append(f"  for (reg i0 = m - {rem_m}; i0 + {rem_m - 1} < m; i0 = i0 + {rem_m}) {{")
        chunks.append(f"    for (reg j0 = 0; {full_j_cond}; j0 = j0 + {S}) {{")
        chunks.append(body(rem_m, S, "j0"))
        chunks.append("    }")
        if rem_p:
            chunks.append(f"    for (reg j0 = p - {rem_p}; j0 + {rem_p - 1} < p; j0 = j0 + {rem_p}) {{")
            chunks.append(body(rem_m, rem_p, "j0"))
            chunks.append("    }")
        chunks.append("  }")
    fn = "\n".join([
        f"void gemm_{case}(ptr_reg A, ptr_reg B, ptr_reg C, ptr_reg buffer)",
        "{",
        "  (void)buffer;",
        *chunks,
        "}",
    ])
    return fn


def crosscheck(shapes):
    """Compile real kernels for a few shapes and diff traces against the simulator."""
    src = ROOT
    work = Path("/tmp/clab-crosscheck")
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(src, work, ignore=shutil.ignore_patterns("manual", ".git", "gemm_traces"))
    results = []
    original = (src / "gemm.cpp").read_text(encoding="utf-8")
    for case, R, S in shapes:
        m, n, p = CASES[case]
        # splice the generated function over the student's function by replacing the whole file's case
        # Easiest: write a gemm.cpp that keeps case0 as baseline-like and puts the kernel in the requested case,
        # and leaves other cases as the original text.
        fn = emit_kernel_cpp(case, R, S)
        text = original
        # replace from "void gemm_caseX" up to the matching undef of p after that function.
        start = text.find(f"void gemm_{case}(")
        end = text.find("#undef p", start)
        if start < 0 or end < 0:
            results.append({"case": case, "R": R, "S": S, "error": "cannot splice"})
            continue
        new_text = text[:start] + fn + "\n\n" + text[end:]
        (work / "gemm.cpp").write_text(new_text, encoding="utf-8")
        trace = work / "gemm_traces" / f"{case}.trace"
        trace.parent.mkdir(exist_ok=True)
        build = subprocess.run(
            ["make", case],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if build.returncode != 0:
            results.append({
                "case": case, "R": R, "S": S,
                "error": "build",
                "tail": "\n".join(build.stdout.splitlines()[-30:] + build.stderr.splitlines()[-30:]),
            })
            continue
        got = load_trace(trace)
        expect = kernel_trace(m, n, p, R, S)
        # register line from make output
        reg_line = next((ln for ln in build.stdout.splitlines() if "Pass using" in ln), "")
        results.append({
            "case": case,
            "R": R,
            "S": S,
            "regs_formula": regs_for(R, S),
            "pass_line": reg_line.strip(),
            "match": got == expect,
            "n_got": len(got),
            "n_expect": len(expect),
            "first_mismatch": None if got == expect else next(
                (i for i, (a, b) in enumerate(zip(got, expect)) if a != b),
                "len",
            ),
        })
    return results


def probe_registers():
    """Compile a tiny program that prints live register counts for each tile shape."""
    shapes = [(4, 4), (4, 6), (4, 3), (3, 6), (3, 3), (2, 8), (5, 4), (1, 1)]
    fns = []
    calls = []
    for R, S in shapes:
        name = f"probe_{R}_{S}"
        lines = [f"void {name}(ptr_reg A, ptr_reg B, ptr_reg C, ptr_reg buffer) {{", "  (void)buffer;"]
        lines.append(f"  for (reg i0 = 0; i0 < {R}; i0 = i0 + {R}) {{")
        lines.append(f"    for (reg j0 = 0; j0 < {S}; j0 = j0 + {S}) {{")
        for r in range(R):
            names = ", ".join(f"c{r}{s} = 0" for s in range(S))
            lines.append(f"      reg {names};")
        lines.append("      for (reg k = 0; k < 1; k = k + 1) {")
        for r in range(R):
            lines.append(f"        reg a{r} = A[{r}];")
        lines.append("        reg b = B[0];")
        for s in range(S):
            if s:
                lines.append(f"        b = B[{s}];")
            lines.append("        " + " ".join(f"c{r}{s} += a{r} * b;" for r in range(R)))
        lines.append(f'        std::cerr << "{R}x{S} inner " << get_current_reg_count() << "\\n";')
        lines.append("      }")
        lines.append(f'      std::cerr << "{R}x{S} after-k " << get_current_reg_count() << "\\n";')
        for r in range(R):
            for s in range(S):
                lines.append(f"      C[{r * S + s}] = c{r}{s};")
        lines.append("    }")
        lines.append("  }")
        lines.append("}")
        fns.append("\n".join(lines))
        calls.append(f"  run({name}, \"{R}x{S}\");")
    src = f'''#include "cachelab.h"
#include <iostream>
{chr(10).join(fns)}
template <typename F>
void run(F fn, const char* name) {{
  max_reg_count = 0;
  auto tup = init(8, 8, 8);
  ptr_reg A = std::move(std::get<0>(tup));
  ptr_reg B = std::move(std::get<1>(tup));
  ptr_reg C = std::move(std::get<2>(tup));
  ptr_reg buffer = std::move(std::get<3>(tup));
  fn(std::move(A), std::move(B), std::move(C), std::move(buffer));
  std::cerr << name << " max " << get_max_reg_count() << "\\n";
}}
int main() {{
{chr(10).join(calls)}
}}
'''
    path = Path("/tmp/probe_regs.cpp")
    path.write_text(src, encoding="utf-8")
    build = subprocess.run(
        ["g++", "-std=c++23", "-O0", "-Wall", "-I", str(ROOT), "-o", "/tmp/probe_regs",
         str(path), str(ROOT / "matrix.cpp")],
        capture_output=True, text=True,
    )
    if build.returncode != 0:
        return {"error": build.stderr[-2000:]}
    run = subprocess.run(["/tmp/probe_regs"], capture_output=True, text=True)
    return {"stdout": run.stdout, "stderr": run.stderr, "code": run.returncode}


def json_dump(obj, path):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crosscheck", action="store_true")
    parser.add_argument("--skip-variants", action="store_true")
    args = parser.parse_args()
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    OUT_GEN.mkdir(parents=True, exist_ok=True)

    print("Comparing simulator traces with official traces...")
    trace_cmp = compare_official_traces()
    for name, info in trace_cmp.items():
        print(f"  {name}: {info}")
    if any(isinstance(v, dict) and not v.get("match", False) for v in trace_cmp.values()):
        raise SystemExit("simulator trace does not match official trace")

    baselines = {}
    students = {}
    for case, (m, n, p) in CASES.items():
        base = simulate_baseline(m, n, p)
        baselines[case] = {
            "miss_cache": base["miss_cache"],
            "miss_reg": base["miss_reg"],
            "latency": base["latency"],
            "stats": base["stats"],
            "a_cat": base["a_cat"],
            "unique_blocks": base["unique_blocks"],
            "b_slice_lines": base["b_slice_lines"],
            "c_store_lines": base["c_store_lines"],
            "b_temporal_hit": base["b_temporal_hit"],
            "c_temporal_hit": base["c_temporal_hit"],
        }
        BASELINE_LAT[case] = base["latency"]
        print(f"baseline {case}: cache {base['miss_cache']} reg {base['miss_reg']} lat {base['latency']} "
              f"A/B/C {base['stats']['A']['miss']}/{base['stats']['B']['miss']}/{base['stats']['C']['miss']}")

    for case, (R, S) in STUDENT.items():
        m, n, p = CASES[case]
        # record the first two j tiles of the first i strip, and for case2 also a later k
        tiles = {(0, 0)}
        # second j tile
        tiles.add((0, S))
        sim = simulate(m, n, p, R, S, record_tiles=tiles)
        pattern = tile_pattern(sim)
        # drop the bulky per-tile list from the pattern copy saved next to summary? keep it.
        students[case] = {
            "R": R, "S": S,
            "regs": regs_for(R, S),
            "miss_cache": sim["miss_cache"],
            "miss_reg": sim["miss_reg"],
            "latency": sim["latency"],
            "speedup": baselines[case]["latency"] / sim["latency"],
            "stats": sim["stats"],
            "a_cat": sim["a_cat"],
            "b_slice_lines": sim["b_slice_lines"],
            "c_store_lines": sim["c_store_lines"],
            "b_temporal_hit": sim["b_temporal_hit"],
            "c_temporal_hit": sim["c_temporal_hit"],
            "unique_blocks": sim["unique_blocks"],
            "pattern_brief": {
                shape: {k: v for k, v in info.items() if k != "tiles"}
                for shape, info in pattern.items()
            },
        }
        write_timeline_tex(case, sim, limit_k=8 if case != "case2" else 8)
        print(f"student {case} {R}x{S}: cache {sim['miss_cache']} reg {sim['miss_reg']} "
              f"lat {sim['latency']} spd {students[case]['speedup']:.4f}")
        print(f"  A cat {sim['a_cat']} B miss {sim['stats']['B']['miss']} vs lines {sim['b_slice_lines']} "
              f"temp {sim['b_temporal_hit']} C miss {sim['stats']['C']['miss']} vs lines {sim['c_store_lines']} "
              f"temp {sim['c_temporal_hit']}")
        print(f"  pattern {students[case]['pattern_brief']}")

    sweeps = {}
    for case in ("case1", "case2", "case3"):
        print(f"sweep {case}...")
        rows = sweep_case(case)
        sweeps[case] = rows
        write_sweep_tex(case, rows, STUDENT[case])
        write_top_tex(case, rows, STUDENT[case])
        best = rows[0]
        print(f"  legal {len(rows)} best {best['R']}x{best['S']} lat {best['latency']} "
              f"spd {best['speedup']:.4f} cache {best['miss_cache']} reg {best['miss_reg']}")
        # rank of student
        for i, r in enumerate(rows):
            if (r["R"], r["S"]) == STUDENT[case]:
                print(f"  student rank {i+1}/{len(rows)}")
                break

    var = {}
    if not args.skip_variants:
        for case, (R, S) in STUDENT.items():
            print(f"variants {case}...")
            var[case] = variants(case, R, S)
            for key, info in var[case].items():
                if key == "kblock_spill":
                    for item in info:
                        print(f"  kc={item['kc']}: cache {item['miss_cache']} reg {item['miss_reg']} lat {item['latency']}")
                else:
                    print(f"  {key}: cache {info['miss_cache']} reg {info['miss_reg']} lat {info['latency']}")

    layouts = {case: describe_shared(*CASES[case]) for case in CASES}
    # speedups and score
    spd = [1.0 if c == "case0" else students[c]["speedup"] for c in ("case0", "case1", "case2", "case3")]
    # case0 speedup is 1
    W = 0.3 * students["case1"]["speedup"] + 0.3 * students["case2"]["speedup"] + 0.4 * students["case3"]["speedup"]
    rate = min(1.0, max(0.0, (W - 1.0) / 7.0))

    summary = {
        "trace_cmp": trace_cmp,
        "baselines": baselines,
        "students": students,
        "layouts": layouts,
        "variants": var,
        "weighted_speedup": W,
        "perf_rate": rate,
        "perf_score": 100 * rate,
        "best": {case: sweeps[case][0] for case in sweeps},
        "n_legal": {case: len(sweeps[case]) for case in sweeps},
        "student_rank": {},
    }
    for case, rows in sweeps.items():
        for i, r in enumerate(rows):
            if (r["R"], r["S"]) == STUDENT[case]:
                summary["student_rank"][case] = {"rank": i + 1, "of": len(rows), "row": r}
    # divisible-only best
    summary["best_divisible"] = {}
    for case, rows in sweeps.items():
        div = [r for r in rows if r["divisible"]]
        summary["best_divisible"][case] = div[0] if div else None

    json_dump(summary, OUT_DATA / "summary.json")
    # sweeps are large because of nothing too big; drop nothing
    json_dump(sweeps, OUT_DATA / "sweeps.json")

    print("Probing register counts...")
    probe = probe_registers()
    (OUT_DATA / "probe_regs.txt").write_text(probe.get("stderr", "") + probe.get("stdout", "") + probe.get("error", ""), encoding="utf-8")
    print(probe.get("stderr", probe.get("error", "")))

    if args.crosscheck:
        shapes = [
            ("case1", 2, 8),
            ("case1", 4, 6),
            ("case1", 5, 4),
            ("case2", 4, 6),
            ("case2", 2, 8),
            ("case3", 3, 6),
            ("case3", 5, 4),
            ("case3", 4, 5),
        ]
        print("Cross-checking real framework...")
        checks = crosscheck(shapes)
        json_dump(checks, OUT_DATA / "crosscheck.json")
        for c in checks:
            print(c if "error" in c else {k: c[k] for k in ("case", "R", "S", "match", "pass_line", "n_got", "regs_formula")})
        if any((not c.get("match", False)) or "error" in c for c in checks):
            raise SystemExit("crosscheck failed")

    print(f"Weighted speedup {W:.6f} score {100*rate:.2f}")
    print("Wrote", OUT_DATA, "and", OUT_GEN)


if __name__ == "__main__":
    main()
