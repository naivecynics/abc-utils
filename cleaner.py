# cleaner.py
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


_Q_RE = re.compile(r'^Q:\s*(.+)$')
_M_RE = re.compile(r'^M:\s*(.+)$')
_K_RE = re.compile(r'^K:\s*(.+)$')
_SCORE_RE = re.compile(r'^%%score\s+(.*)$')
_V_RE = re.compile(r'^V:\s*(\d+)\b(.*)$')
_V_INLINE_Q_RE = re.compile(r'(\[V:\s*\d+\])\s*(\[Q:[^\]]+\])')
_ANY_Q_INLINE_RE = re.compile(r'\[Q:[^\]]+\]')
_V_TAGGED_SEG_RE = re.compile(r'\[V:\s*(\d+)\]')

# minimal, ASCII-only “treble” -> “treb”
def _shorten_clef(text: str) -> str:
    return text.replace("treble", "treb")

@dataclass
class Encoded:
    text: str


class ABCCleaner:
    def encode(self, abc_text: str) -> Encoded:
        # normalize EOLs and ascii-ify clef token
        text = _shorten_clef(abc_text).replace('\r\n', '\n').replace('\r', '\n')

        # split to lines and drop empty lines
        lines = [ln for ln in text.split('\n') if ln.strip()]

        # split header vs bars (header: "X:"-style or "%%")
        header, bars = self._split_header_bars(lines)

        # remove L:1/8 lines from header
        header = [ln for ln in header if not ln.startswith('L:1/8')]

        # extract key header entities
        q_val = self._pick_once(header, _Q_RE)     # "1/4=160" etc.
        m_val = self._pick_once(header, _M_RE)     # "2/2" etc.
        k_val = self._pick_once(header, _K_RE)     # "C", "Eb", "none" etc.
        score_body = self._pick_once(header, _SCORE_RE)  # score grammar after %%score

        # collect V-lines + percussive K/I “region” blocks
        vmeta, percussive_inline = self._collect_v_and_percmap(header)

        # downflow %%score into grouping map for tagging and 1st-line tags
        group_map = self._build_group_map(score_body) if score_body else {}

        # broadcast snm inside the smallest available group (paren > single)
        self._broadcast_snm(vmeta, group_map)

        # build the compact header:
        #   - drop Q/M/K/%%score and percussive K/I lines (moved to 1st bar)
        #   - render tagged V-lines:  "V:17 bass -12 Cb. (17|18)" etc.
        compact_header = self._render_tagged_v_header(vmeta, group_map)

        # inject Q/M/K (+ percussive overrides and [I:...] list) into first bar line
        bars = self._ensure_bars(bars)
        if bars:
            bars[0] = self._inject_first_line_tags(
                bars[0],
                q_val=q_val,
                m_val=m_val,
                k_default=k_val,
                vmeta=vmeta,
                group_map=group_map,
                perc_inline=percussive_inline,
            )

        # drop any [Q:...] not adjacent to [V:n]
        bars = [self._strip_floating_q(line) for line in bars]
        # drop all space
        bars = [re.sub(r'\s+', '', line) for line in bars]

        # final serialize
        out = '\n'.join(compact_header + bars)
        return Encoded(text=out)

    def decode(self, cleaned_text: str) -> str:
        # best-effort passthrough; no exact inverse
        return cleaned_text

    # ---------------- core helpers ----------------

    def _split_header_bars(self, lines: List[str]) -> Tuple[List[str], List[str]]:
        header, body = [], []
        in_body = False
        for ln in lines:
            if not in_body and (self._is_header(ln)):
                header.append(ln)
            else:
                in_body = True
                body.append(ln)
        return header, body

    def _is_header(self, line: str) -> bool:
        s = line.strip()
        return (len(s) >= 2 and s[0].isalpha() and s[1] == ':') or s.startswith('%%')

    def _pick_once(self, header: List[str], rx: re.Pattern) -> Optional[str]:
        for ln in header:
            m = rx.match(ln.strip())
            if m:
                return m.group(1).strip()
        return None

    def _collect_v_and_percmap(self, header: List[str]):
        """
        Parse all V-lines; capture clef, transpose, nm, snm.
        Detect percussive K:none and following I:percmap lines assigned to the last perc V.
        """
        vmeta: Dict[int, Dict] = {}
        percussive_inline: Dict[int, Dict[str, List[str]]] = {}

        last_vid: Optional[int] = None
        last_is_perc = False

        for ln in header:
            # V-line
            vm = _V_RE.match(ln.strip())
            if vm:
                vid = int(vm.group(1))
                payload = vm.group(2).strip()
                clef, transpose, nm, snm = self._parse_v_payload(payload)
                vmeta[vid] = {
                    "clef": clef,
                    "transpose": transpose,
                    "nm": nm,
                    "snm": snm,
                }
                last_vid = vid
                last_is_perc = (clef == "perc")
                continue

            # K:none right after a perc V should override key on first line for that V
            km = _K_RE.match(ln.strip())
            if km and last_vid is not None and last_is_perc:
                kval = km.group(1).strip()
                if kval.lower() == "none":
                    percussive_inline.setdefault(last_vid, {}).setdefault("K", []).append("none")
                continue

            # I:percmap lines assigned to the last perc V
            if ln.startswith("I:percmap") and last_vid is not None and last_is_perc:
                percussive_inline.setdefault(last_vid, {}).setdefault("I", []).append(ln.strip())

        return vmeta, percussive_inline

    def _parse_v_payload(self, payload: str) -> Tuple[str, int, str, str]:
        # clef token is the first bare word if present
        clef = ""
        transpose = 0
        nm, snm = "", ""

        # tokenize by spaces but keep key=val tokens
        toks = payload.split()

        # clef = first non key=value token
        m = re.search(r'clef\s*=\s*([A-Za-z]+)\s*([+-]\d+)?', payload)
        if m:
            base = (m.group(1) or '').lower()
            octv = (m.group(2) or '')
            clef = base + octv
        else:
            for t in toks:
                if '=' not in t:
                    clef = t
                    break
            clef = (clef or "").lower()

        # transpose
        m = re.search(r'transpose\s*=\s*(-?\d+)', payload)
        if m:
            try:
                transpose = int(m.group(1))
            except:
                transpose = 0

        # nm, snm
        nm_m = re.search(r'nm="([^"]*)"', payload)
        snm_m = re.search(r'snm="([^"]*)"', payload)
        if nm_m:
            nm = nm_m.group(1).strip()
        if snm_m:
            snm = snm_m.group(1).strip()

        return clef, transpose, nm, snm

    # ---------- score parsing to build group map ----------

    def _build_group_map(self, score_body: str) -> Dict[int, str]:
        """
        Build a map vid -> group_string.
        Braces have priority over parens for the final label.
        """
        tokens = self._score_tokenize(score_body)
        stack: List[Dict] = []  # nodes: {"type": '('{ or '{', "elems": [str], "nums": set()}
        paren_map: Dict[int, str] = {}
        brace_map: Dict[int, str] = {}

        def flush_group(node):
            t = node["type"]
            elems = node["elems"]
            nums = node["nums"]
            if t == '(':
                s = '(' + '|'.join(elems) + ')'
                for n in nums:
                    paren_map.setdefault(n, s)
                return s, nums
            else:
                s = '{' + '|'.join(elems) + '}'
                for n in nums:
                    brace_map.setdefault(n, s)
                return s, nums

        i = 0
        while i < len(tokens):
            tk = tokens[i]
            if tk in ('(', '{'):
                stack.append({"type": tk, "elems": [], "nums": set()})
            elif tk in (')', '}'):
                if stack:
                    node = stack.pop()
                    if (node["type"] == '(' and tk != ')') or (node["type"] == '{' and tk != '}'):
                        # ignore malformed
                        pass
                    s, ns = flush_group(node)
                    if stack:
                        stack[-1]["elems"].append(s)
                        stack[-1]["nums"].update(ns)
                # else: stray closer -> ignore
            elif tk == '|':
                # separators inside groups are implicit via join, skip
                pass
            else:
                # number
                try:
                    n = int(tk)
                except:
                    i += 1
                    continue
                if stack:
                    stack[-1]["elems"].append(str(n))
                    stack[-1]["nums"].add(n)
                else:
                    # top-level single -> no paren/brace; still useful as singleton
                    paren_map.setdefault(n, f'({n})')
            i += 1

        # prefer brace group if exists, else paren group
        group_map: Dict[int, str] = {}
        for n, s in paren_map.items():
            group_map[n] = s
        for n, s in brace_map.items():
            group_map[n] = s  # override with brace priority
        return group_map

    def _score_tokenize(self, body: str) -> List[str]:
        out = []
        i = 0
        while i < len(body):
            c = body[i]
            if c.isspace():
                i += 1
                continue
            if c in '(){}|':
                out.append(c)
                i += 1
                continue
            if c.isdigit():
                j = i
                while j < len(body) and body[j].isdigit():
                    j += 1
                out.append(body[i:j])
                i = j
                continue
            i += 1
        return out

    # ---------- snm broadcast inside group ----------

    def _broadcast_snm(self, vmeta: Dict[int, Dict], group_map: Dict[int, str]):
        # build group key -> vids
        g2vids: Dict[str, List[int]] = {}
        for vid in vmeta.keys():
            gkey = group_map.get(vid, f'({vid})')
            g2vids.setdefault(gkey, []).append(vid)

        for gkey, vids in g2vids.items():
            leader = ""
            # pick first non-empty snm
            for v in sorted(vids):
                snm = (vmeta.get(v, {}).get("snm") or "").strip()
                if snm:
                    leader = snm
                    break
            if not leader:
                continue
            for v in vids:
                if not (vmeta.get(v, {}).get("snm") or "").strip():
                    vmeta[v]["snm"] = leader

    # ---------- header rendering ----------

    def _render_tagged_v_header(self, vmeta: Dict[int, Dict], group_map: Dict[int, str]) -> List[str]:
        out = []
        for vid in sorted(vmeta.keys()):
            meta = vmeta[vid]
            raw_clef = (meta.get("clef") or "").strip().lower()

            clef = ""
            if raw_clef:
                m = re.match(r'([a-z]+)([+-]\d+)?$', raw_clef)
                if m:
                    base, octv = m.group(1), (m.group(2) or "")
                    clef = base[:4] + octv  # e.g. treble+8 -> treb+8
                else:
                    clef = raw_clef[:4]

            tran = int(meta.get("transpose") or 0)
            snm = (meta.get("snm") or "").replace(" ", "")
            gkey = group_map.get(vid, f'({vid})')

            parts = [f"V:{vid}"]
            if clef:
                parts.append(clef)
            parts.append(str(tran))
            if snm:
                parts.append(snm)
            parts.append(gkey)
            out.append(' '.join(parts))
        return out

    # ---------- bars manipulation ----------

    def _ensure_bars(self, bars: List[str]) -> List[str]:
        # ensure each bar line is single logical line (already is)
        return bars[:]

    def _inject_first_line_tags(
        self,
        line: str,
        *,
        q_val: Optional[str],
        m_val: Optional[str],
        k_default: Optional[str],
        vmeta: Dict[int, Dict],
        group_map: Dict[int, str],
        perc_inline: Dict[int, Dict[str, List[str]]],
    ) -> str:
        parts = []
        pos = 0
        for m in _V_TAGGED_SEG_RE.finditer(line):
            start, end = m.span()
            if start > pos:
                parts.append(line[pos:start])
            parts.append(line[start:end])
            pos = end
        if pos < len(line):
            parts.append(line[pos:])

        first_q_done = False
        m_done = False   # 新增：M 只注入一次，且仅在 V:1
        result_parts = []
        i = 0
        while i < len(parts):
            seg = parts[i]
            vm = _V_TAGGED_SEG_RE.match(seg)
            if vm:
                vid = int(vm.group(1))
                inject = []

                # Q: 仅在 V:1 后注入一次
                if not first_q_done and q_val is not None and vid == 1:
                    inject.append(f"[Q:{q_val}]")
                    first_q_done = True

                # M: 仅在 V:1 后注入一次
                if not m_done and m_val is not None and vid == 1:
                    inject.append(f"[M:{m_val}]")
                    m_done = True

                # K: 逻辑保持不变（每个声部都保证有 K，打击乐可用 none 覆盖）
                seg_tail = parts[i + 1] if (i + 1) < len(parts) else ""
                has_inline_k = "[K:" in seg_tail
                perc_k = None
                if vid in perc_inline and "K" in perc_inline[vid]:
                    perc_k = "none"
                if perc_k is not None:
                    inject.append(f"[K:{perc_k}]")
                elif (not has_inline_k) and k_default is not None:
                    inject.append(f"[K:{k_default}]")

                if vid in perc_inline and "I" in perc_inline[vid]:
                    for il in perc_inline[vid]["I"]:
                        inject.append(f"[{il}]")

                result_parts.append(seg + ''.join(inject))
                i += 1
                continue

            result_parts.append(seg)
            i += 1

        return ''.join(result_parts)

    def _strip_floating_q(self, line: str) -> str:
        """
        Remove any [Q:...] that is not immediately after a [V:n].
        """
        # protect legal “[V:n][Q:…]” combos by temporarily marking them
        protected = _V_INLINE_Q_RE.sub(lambda m: m.group(1) + "<QPROTECTED>" + m.group(2)[1:-1] + "</QPROTECTED>", line)
        # drop all [Q:...]
        stripped = _ANY_Q_INLINE_RE.sub('', protected)
        # restore protected
        restored = stripped.replace("<QPROTECTED>", "[").replace("</QPROTECTED>", "]")
        return restored
