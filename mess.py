# restore_abc_simple.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional
from tqdm import tqdm

# 你的目录
ORI_DIRS = ["./data/classical_interleaved_cleaned/"]
TAR_DIRS = ["./data/classical_interleaved_restored/"]

# ---------- 基础工具 ----------
def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def write_text(p: Path, s: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8", newline="\n")

def split_head_body(abc: str) -> Tuple[List[str], List[str]]:
    head, body = [], []
    for ln in abc.splitlines():
        if not ln.strip():
            continue
        if ln[0].isalpha() and ln[1:2] == ":":
            head.append(ln)
        else:
            body.append(ln)
    return head, body

# ---------- 从正文探一次 Q/M/K（不改正文） ----------
RE_TAG_Q = re.compile(r"\[Q:[^\]]+\]")
RE_TAG_M = re.compile(r"\[M:[^\]]+\]")
RE_TAG_K = re.compile(r"\[K:([^\]]+)\]")

def probe_qmk_from_body(body_lines: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    q = m = k = None
    for ln in body_lines:
        if q is None:
            mq = RE_TAG_Q.search(ln)
            if mq: q = mq.group(0)[1:-1]  # 去掉方括号
        if m is None:
            mm = RE_TAG_M.search(ln)
            if mm: m = mm.group(0)[1:-1]
        if k is None:
            mk = RE_TAG_K.search(ln)
            if mk:
                kval = mk.group(1).strip()
                if kval.lower() != "none":
                    k = f"K:{kval}"
        if q and m and k:
            break
    return q, m, k

# ---------- V 行解析（严格 5 段：V:<id> clef transpose name group） ----------
CLEF_MAP = {
    "treb": "treble", "treble": "treble",
    "alto": "alto",
    "bass": "bass",
    "perc": "perc",
}

@dataclass
class VDef:
    vid: int
    clef: str
    transpose: int
    name: str
    group: Optional[str]  # "(1|2|3)" 或 "{(5|7|8)|(6|9|10)}"

def parse_vdefs_simple(lines: List[str]) -> List[VDef]:
    out: List[VDef] = []
    for ln in lines:
        if not ln.startswith("V:"):  # 只吃简化后的 V 行
            continue
        parts = ln.split(maxsplit=4)  # 强制五段
        if len(parts) < 5:
            # 没有分组也兼容：V:<id> clef transpose name
            parts = ln.split(maxsplit=3)
            if len(parts) < 4:
                continue
            vraw, clef, trp, name = parts
            grp = None
        else:
            vraw, clef, trp, name, grp = parts
        try:
            vid = int(vraw.split(":")[1])
        except:
            continue
        clef_n = CLEF_MAP.get(clef.lower(), clef)
        try:
            trp_i = int(trp)
        except:
            trp_i = 0
        grp = (grp or "").strip()
        # 只接受括号或大括号形式
        if grp and not ((grp.startswith("(") and grp.endswith(")")) or (grp.startswith("{") and grp.endswith("}"))):
            grp = None
        out.append(VDef(vid=vid, clef=clef_n, transpose=trp_i, name=name, group=grp if grp else None))
    out.sort(key=lambda x: x.vid)
    return out

# ---------- 组装 score ----------
def _split_top_level_pipes(s: str) -> list[str]:
    """只在顶层分割 '|'，括号/大括号内的 '|' 会被忽略。"""
    out, buf, lvl = [], [], 0
    for ch in s:
        if ch in "({":
            lvl += 1
            buf.append(ch)
        elif ch in ")}":
            lvl -= 1
            buf.append(ch)
        elif ch == "|" and lvl == 0:
            tok = "".join(buf).strip()
            if tok:
                out.append(tok)
            buf = []
        else:
            buf.append(ch)
    tok = "".join(buf).strip()
    if tok:
        out.append(tok)
    return out

def _norm_paren_token(s: str) -> str:
    # "(5|7|8)" -> "( 5 7 8 )"; 单个数 -> "5"
    inner = s.strip()[1:-1].strip()
    nums = [int(x) for x in inner.split("|") if x.strip().isdigit()]
    if not nums:
        return "( )"
    return str(nums[0]) if len(nums) == 1 else "( " + " ".join(map(str, nums)) + " )"

def _norm_brace_token(s: str) -> str:
    # "{(5|7|8)|(6|9|10)}" -> "{ ( 5 7 8 ) | ( 6 9 10 ) }"
    inner = s.strip()[1:-1].strip()
    arms = _split_top_level_pipes(inner)  # 只在顶层切
    norm_arms = []
    for arm in arms:
        arm = arm.strip()
        if not arm:
            continue
        if arm.startswith("(") and arm.endswith(")"):
            norm_arms.append(_norm_paren_token(arm))
        else:
            # 兼容裸 "5|6|7" 或单个 "22"
            parts = _split_top_level_pipes(arm)
            nums = []
            for p in parts:
                p = p.strip()
                if p.isdigit():
                    nums.append(int(p))
            if not nums:
                continue
            norm_arms.append(str(nums[0]) if len(nums) == 1 else "( " + " ".join(map(str, nums)) + " )")
    if not norm_arms:
        return "{ }"
    return "{ " + " | ".join(norm_arms) + " }"

def _group_members(s: str) -> list[int]:
    """把组串还原为成员 id 列表：支持 '(...)' 和 '{ ... | ... }'（顶层分割）"""
    s = s.strip()
    if s.startswith("(") and s.endswith(")"):
        inner = s[1:-1].strip()
        return [int(x) for x in inner.split("|") if x.strip().isdigit()]
    if s.startswith("{") and s.endswith("}"):
        inner = s[1:-1].strip()
        ids: list[int] = []
        for arm in _split_top_level_pipes(inner):
            arm = arm.strip()
            if not arm:
                continue
            if arm.startswith("(") and arm.endswith(")"):
                inner_p = arm[1:-1].strip()
                ids.extend([int(x) for x in inner_p.split("|") if x.strip().isdigit()])
            else:
                # 裸 arm：顶层再切并收集数字
                for p in _split_top_level_pipes(arm):
                    p = p.strip()
                    if p.isdigit():
                        ids.append(int(p))
        return ids
    return []

def build_score_tokens_in_appearance(vdefs: List[VDef]) -> Tuple[List[str], dict[int, str]]:
    """
    返回 (score_tokens, rep_for_nm):
      - score_tokens：按 **首次出现顺序** 输出分组（括号/大括号均可），其后输出所有未分组的单独 V。
      - rep_for_nm：每个 vid 是否是其组代表（仅代表写 nm/snm）。单声部也写。
    """
    seen_group_keys = set()
    tokens: List[str] = []
    grouped_members: set[int] = set()
    rep_for_nm: dict[int, str] = {}

    def group_key(g: str) -> str:
        # 规范化为稳定 key
        ids = _group_members(g)
        if g.startswith("("):
            return "P:" + ",".join(map(str, sorted(ids)))
        return "B:" + ",".join(map(str, sorted(ids)))

    # 先按出现顺序把“还没输出过的组”推入 tokens
    for v in vdefs:
        if v.group:
            key = group_key(v.group)
            if key not in seen_group_keys:
                seen_group_keys.add(key)
                ids = _group_members(v.group)
                grouped_members.update(ids)
                # 代表是组内最小 id
                rep = min(ids) if ids else v.vid
                rep_for_nm[rep] = v.group  # 记录代表对应的原始组串（仅用于标记代表）
                # 规范化 token
                tok = _norm_paren_token(v.group) if v.group.startswith("(") else _norm_brace_token(v.group)
                tokens.append(tok)

    # 再把没分组过的单独声部按编号升序放在后面
    singles = [v.vid for v in vdefs if v.vid not in grouped_members]
    tokens.extend([str(x) for x in singles])

    # 单独声部也作为自己的代表（便于下游写 nm/snm）
    for x in singles:
        rep_for_nm.setdefault(x, "")

    return tokens, rep_for_nm

# ---------- 渲染表头 ----------
def render_head(vdefs: List[VDef], body_lines: List[str]) -> List[str]:
    score_tokens, rep_for_nm = build_score_tokens_in_appearance(vdefs)
    head = ["%%score " + " ".join(score_tokens), "L:1/8"]

    q, m, k = probe_qmk_from_body(body_lines)
    if q: head.append(q)
    if m: head.append(m)
    if k: head.append(k)

    v_lines: List[str] = []
    for v in vdefs:
        fields = [f"V:{v.vid}", v.clef]
        if v.clef == "perc":
            fields.append("stafflines=1")
        if v.transpose != 0:
            fields.append(f"transpose={v.transpose}")

        # nm/snm：组代表 或 单声部 才写；其它组员不写
        is_rep = v.vid in rep_for_nm
        if is_rep and v.name:
            fields += [f'nm="{v.name}"', f'snm="{v.name}"']

        v_lines.append(" ".join(fields))

    return head + v_lines

# ---------- 主还原 ----------
def restore_text_simple(abc_cleaned: str) -> str:
    head, body = split_head_body(abc_cleaned)
    vdefs = parse_vdefs_simple(head)
    if not vdefs:
        return "\n".join(head + body) + ("\n" if (head or body) else "")
    head_out = render_head(vdefs, body)
    return "\n".join(head_out + body) + "\n"

def process_file(src: Path, dst_root: Path):
    raw = read_text(src)
    restored = restore_text_simple(raw)
    rel = src.relative_to(src.parents[0])
    dst = dst_root.joinpath(rel)
    write_text(dst, restored)

def main():
    if len(ORI_DIRS) != len(TAR_DIRS):
        raise ValueError("ORI_DIRS and TAR_DIRS must have the same length")
    for ori, tar in zip(ORI_DIRS, TAR_DIRS):
        sroot = Path(ori)
        troot = Path(tar).resolve()
        troot.mkdir(parents=True, exist_ok=True)
        if not sroot.exists():
            print(f"[WARN] path not found: {ori}")
            continue
        files = list(sroot.rglob("*.abc"))
        for f in tqdm(files, desc=f"Restoring {ori}"):
            try:
                process_file(f, troot)
            except Exception as e:
                print(f"[ERROR] {f}: {e}")

if __name__ == "__main__":
    main()
