from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import datetime as _dt

# =============================================================================
# ----------------------------- Core Tlog Parsing ------------------------------
# =============================================================================
import re

_TIMESTAMP_PREFIX_RE = re.compile(
    r'^\s*\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\]\s*'
)

def _strip_timestamp_prefix(lines):
    """
    Remove leading timestamp like:
    [2025-07-25 02:23:49.875]
    from each line if present.
    """
    out = []
    for line in lines:
        new_line = _TIMESTAMP_PREFIX_RE.sub('', line)
        out.append(new_line)
    return out

def _canonicalize_header_line(line: str) -> str:
    """
    Normalize header line for robust detection.
    - commas -> space
    - tabs -> space
    - collapse multiple spaces
    - lowercase
    """
    s = line.replace(',', ' ').replace('\t', ' ')
    s = ' '.join(s.split())
    return s.lower()

def _make_unique_header(cols: List[str]) -> List[str]:
    seen = {}
    out = []
    for c in cols:
        base = c

        # special duplicate names
        if base in seen:
            if base == "adc":
                base = "adc2"
            elif base == "C1c,f":
                base = "C1c,f2"
            elif base == "C2c,f":
                base = "C2c,f2"

        if base in seen:
            k = seen[base] + 1
            new_name = f"{base}_{k}"
            while new_name in seen:
                k += 1
                new_name = f"{base}_{k}"
            seen[base] = k
            out.append(new_name)
            seen[new_name] = 1
        else:
            seen[base] = 1
            out.append(base)

    return out

import re

def _tok_norm(s: str) -> str:
    # keep only letters/numbers so '_ms.' -> 'ms'
    return re.sub(r'[^a-z0-9]+', '', s.lower())

def _line_has_sec_ms(line: str) -> bool:
    # allow commas / spaces / tabs etc.
    tokens = line.replace(',', ' ').replace('\t', ' ').split()
    has_sec = any(_tok_norm(t) == 'sec' for t in tokens)
    has_ms  = any(_tok_norm(t) == 'ms'  for t in tokens)
    return has_sec and has_ms

def _find_all_data_headers(lines: List[str]) -> List[Tuple[int, List[str], int]]:
    """
    Find all occurrences of the data header line and corresponding data_start.
    Returns list of tuples: (header_idx, header_tokens, data_start_idx)

    Task I-06 fix:
      - Accept both 'sec,_ms.' (single token) and 'sec ms' (two tokens),
        regardless of comma/space/tab delimiters.
      - Still requires Pls/Freq/Pfwd so we don't accidentally match data rows.
    """
    import re

    def _tok_norm(tok: str) -> str:
        # normalize token to alnum only, lowercase
        # examples:
        #   "sec,_ms." -> "secms"
        #   "Rf:UC-S"  -> "rfucs"
        return re.sub(r"[^a-z0-9]+", "", tok.lower())

    hits: List[Tuple[int, List[str], int]] = []

    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s:
            continue

        # Normalize common RF token casing to avoid header mismatch later
        s_norm = s.replace("Rf:", "RF:").replace("rf:", "RF:")

        # Tokenize (do NOT destroy original spacing; split() is fine)
        raw_tokens = s_norm.split()
        norm_tokens = [_tok_norm(t) for t in raw_tokens]

        # ---- Header detection rules ----
        # Time columns can appear as:
        #   - "sec,_ms."  -> norm "secms"
        #   - "sec" "ms"  -> norm tokens contain both "sec" and "ms"
        time_ok = ("secms" in norm_tokens) or ("sec" in norm_tokens and "ms" in norm_tokens)

        # Common header columns (both Tykon and Chronos2.0 have these)
        # Using normalized tokens makes it delimiter-robust.
        must_ok = ("pls" in norm_tokens) and ("freq" in norm_tokens)

        # Require at least Pfwd in header to avoid matching non-data text lines
        pfwd_ok = ("pfwd" in norm_tokens)

        if time_ok and must_ok and pfwd_ok:
            header_tokens = raw_tokens

            # compute data_start: after dashed separator line if present
            data_start = i + 1
            for j in range(i + 1, min(i + 25, len(lines))):
                if lines[j].strip().startswith("----------"):
                    data_start = j + 1
                    break

            hits.append((i, header_tokens, data_start))

    return hits

def _normalize_header(tokens: List[str]) -> List[str]:
    # ---- Task I-06: Chronos 2.0 header fix ----
    # Chronos 2.0 may write the time header as two tokens: "sec  ms"
    # but data rows use one token like "8,633.20". We normalize to the
    # canonical single token used everywhere else: "sec,_ms."
    if len(tokens) >= 2:
        t0 = tokens[0].strip().lower()
        t1 = tokens[1].strip().lower()
        if t0 == "sec" and t1 == "ms":
            tokens = ["sec,_ms."] + tokens[2:]
    # ------------------------------------------
    expanded: List[str] = []
    for t in tokens:
        t2 = t.replace("Rf:", "RF:").replace("rf:", "RF:")
        if t2 == "RF:UC-S":
            expanded.extend(["RF:UC", "RF:S"])
        else:
            expanded.append(t2)
    return _make_unique_header(expanded)

# def _parse_data_rows(lines: List[str], header: List[str], data_start_idx: int, data_end_idx: Optional[int] = None) -> pd.DataFrame:
#     """
#     Parse data rows for both:
#       - Tykon: starts with sec,_ms token
#       - Quantum: starts with MN PSx sec,_ms token
#
#     We identify time token by header index of 'sec,_ms.'.
#
#     data_end_idx: if provided, stop parsing before this line index.
#     """
#     if "sec,_ms." not in header:
#         raise ValueError("Header missing 'sec,_ms.'")
#
#     time_idx = header.index("sec,_ms.")
#     time_pat = re.compile(r"^\d+,\d+(\.\d+)?$")
#
#     end = data_end_idx if (data_end_idx is not None) else len(lines)
#
#     rows = []
#     for ln in lines[data_start_idx:end]:
#         s = ln.strip()
#         if not s:
#             continue
#         if s.startswith("//") or s.startswith("----------"):
#             continue
#
#         parts = s.split()
#         if len(parts) <= time_idx:
#             continue
#
#         if not time_pat.match(parts[time_idx]):
#             continue
#
#         if len(parts) < len(header):
#             parts = parts + [None] * (len(header) - len(parts))
#         elif len(parts) > len(header):
#             extras = parts[len(header) - 1:]
#             parts = parts[:len(header) - 1] + [" ".join([p for p in extras if p is not None])]
#
#         rows.append(parts)
#
#     return pd.DataFrame(rows, columns=header)

def _parse_data_rows(lines: List[str], header: List[str], data_start_idx: int, data_end_idx: Optional[int] = None) -> pd.DataFrame:
    """
    Parse data rows for both:
      - Tykon: starts with sec,_ms token
      - Quantum: starts with MN PSx sec,_ms token
      - Chronos 2.0: sec ms in header but data rows still have time token like 8,633.20

    We identify time token by header index of 'sec,_ms.'.

    Fix (Task I): C1c,f and C2c,f sometimes appear as '0, 0' (with a space),
    which breaks naive split() tokenization. We merge such pairs back into one token.
    """
    if "sec,_ms." not in header:
        raise ValueError("Header missing 'sec,_ms.'")

    time_idx = header.index("sec,_ms.")
    time_pat = re.compile(r"^\d+,\d+(\.\d+)?$")

    # Indices for the problematic cap tokens (if present)
    try:
        c1_idx = header.index("C1c,f")
    except ValueError:
        c1_idx = None
    try:
        c2_idx = header.index("C2c,f")
    except ValueError:
        c2_idx = None

    num_pat = re.compile(r"^\d+(\.\d+)?$")   # allow int/float
    end = data_end_idx if (data_end_idx is not None) else len(lines)

    def _merge_cap_token(parts: List[str], idx: int) -> List[str]:
        """
        If parts[idx] looks like '0,' and parts[idx+1] looks like '0',
        merge into '0,0' and remove parts[idx+1].
        """
        if idx is None:
            return parts
        if idx < 0 or idx >= len(parts) - 1:
            return parts

        a = parts[idx]
        b = parts[idx + 1]

        # Example: a='0,' b='0' OR a='6,' b='63'
        if isinstance(a, str) and isinstance(b, str):
            if a.endswith(",") and num_pat.match(b):
                parts = parts[:idx] + [a + b] + parts[idx + 2:]
        return parts

    rows = []
    for ln in lines[data_start_idx:end]:
        s = ln.strip()
        if not s:
            continue
        if s.startswith("//") or s.startswith("----------"):
            continue

        parts = s.split()
        if len(parts) <= time_idx:
            continue

        # must have valid time token at time_idx
        if not time_pat.match(parts[time_idx]):
            continue

        # ---- Task I: fix tokenization for C1c,f and C2c,f ('0, 0' -> '0,0') ----
        # We may need to merge twice because merging C1 can shift C2 position.
        if c1_idx is not None:
            parts = _merge_cap_token(parts, c1_idx)
        if c2_idx is not None:
            # if C2 is after C1 and C1 merged, C2 index might shift by -1 if the split happened before C2
            # safest approach: re-find by name using current header index (header stays constant),
            # but token list can be shorter; we just attempt merge at c2_idx and also at c2_idx-1.
            parts = _merge_cap_token(parts, c2_idx)
            parts = _merge_cap_token(parts, c2_idx - 1)
        # -----------------------------------------------------------------------

        # Now align to header length safely
        if len(parts) < len(header):
            parts = parts + [None] * (len(header) - len(parts))
        elif len(parts) > len(header):
            # If still longer, join the tail into the last column (legacy behavior)
            extras = parts[len(header) - 1:]
            parts = parts[:len(header) - 1] + [" ".join([p for p in extras if p is not None])]

        rows.append(parts)

    return pd.DataFrame(rows, columns=header)

@dataclass
class CleanStats:
    vcap_lines_deleted: int = 0
    junk_lines_deleted: int = 0
    pref_lines_deleted: int = 0
    setpt_lines_deleted: int = 0
    pref_gt_pfwd_deleted: int = 0
    arrow_lines_deleted: int = 0
    pipe_lines_deleted: int = 0
    remain_valid_lines: int = 0

def _clean_like_jsl(df: pd.DataFrame) -> Tuple[pd.DataFrame, CleanStats]:
    stats = CleanStats()
    df = df.copy()

    # -----------------------------
    # 1) Remove junk rows (Section / |)
    # NOTE: DO NOT filter by '->' here; it is a real token/column in your tlog format. [1](https://oneasm-my.sharepoint.com/personal/victor_huang_asm_com/Documents/Microsoft%20Copilot%20Chat%20Files/013-30_53300212_20260225-182102_tlog%20-%202nd%20header.txt)
    # -----------------------------
    row_text = df.apply(lambda r: " ".join(map(str, r.values)), axis=1)
    junk_mask = row_text.str.contains("Section", case=False, na=False)
    stats.junk_lines_deleted = int(junk_mask.sum())
    df = df.loc[~junk_mask].copy()

    # -----------------------------
    # Remove corrupt rows: separator token columns must match their literal tokens
    # -----------------------------
    if "->" in df.columns:
        arrow = df["->"].astype(str).str.strip()
        m = (arrow != "->")
        stats.arrow_lines_deleted = int(m.sum())
        df = df.loc[~m].copy()

    if "|" in df.columns:
        pipe = df["|"].astype(str).str.strip()
        m = (pipe != "|")
        stats.pipe_lines_deleted = int(m.sum())
        df = df.loc[~m].copy()

    # -----------------------------
    # 1b) Remove corrupt rows: column '->' must equal literal '->'
    # -----------------------------
    if "->" in df.columns:
        arrow = df["->"].astype(str).str.strip()
        m = (arrow != "->")  # treat blanks/NaN as corrupt too
        stats.arrow_lines_deleted = int(m.sum())
        df = df.loc[~m].copy()

    # -----------------------------
    # 2) Remove Vcap >= 1300
    # -----------------------------
    if "Vcap" in df.columns:
        vcap = pd.to_numeric(df["Vcap"], errors="coerce")
        m = (vcap >= 1300)
        stats.vcap_lines_deleted = int(m.sum())
        df = df.loc[~m].copy()

    # -----------------------------
    # 3) Remove Pref > 2000
    # -----------------------------
    if "Pref" in df.columns:
        pref = pd.to_numeric(df["Pref"], errors="coerce")
        m = (pref > 2000)
        stats.pref_lines_deleted = int(m.sum())
        df = df.loc[~m].copy()

    # -----------------------------
    # 4) Remove SetPt/Pset > 4000 (keep margin)
    # -----------------------------
    setpt_cols = [c for c in ("SetPt", "Pset") if c in df.columns]
    if setpt_cols:
        m_any = np.zeros(len(df), dtype=bool)
        for c in setpt_cols:
            sp = pd.to_numeric(df[c], errors="coerce")
            m_any |= (sp > 4000).fillna(False).to_numpy()

        stats.setpt_lines_deleted = int(m_any.sum())
        df = df.loc[~m_any].copy()

    # -----------------------------
    # 5) Remove impossible: Pref > Pfwd (physics)
    # -----------------------------
    if "Pref" in df.columns and "Pfwd" in df.columns:
        pref = pd.to_numeric(df["Pref"], errors="coerce")
        pfwd = pd.to_numeric(df["Pfwd"], errors="coerce")
        m = pref.notna() & pfwd.notna() & (pref > pfwd)
        stats.pref_gt_pfwd_deleted = int(m.sum())
        df = df.loc[~m].copy()

    stats.remain_valid_lines = int(len(df))
    return df, stats

def _derive_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["row()"] = range(1, len(df) + 1)

    sec_ms = df["sec,_ms."].astype(str).str.split(",", n=1, expand=True)
    df["time(s)"] = pd.to_numeric(sec_ms[0], errors="coerce")
    df["time(ms)"] = pd.to_numeric(sec_ms[1], errors="coerce")

    baseline = df["time(s)"].iloc[1] if len(df) >= 2 else df["time(s)"].iloc[0]
    df["time0(s)"] = df["time(s)"] - baseline
    df["t(s)"] = df["time0(s)"] + df["time(ms)"] / 1000.0

    # ----------------------------------------------------------
    # Pulse mode decode: Pls -> Pmode (numeric)
    # CW mode: Pls starts with 'n' (lowercase) => Pmode = 0
    # Pulse mode: Pls starts with 'Y' (uppercase) => Pmode = 1
    # ----------------------------------------------------------
    if "Pls" in df.columns:
        pls0 = df["Pls"].astype(str).str.strip()

        # Extract 1st and 2nd characters safely
        ch0 = pls0.str.slice(0, 1)  # first char
        ch1 = pls0.str.slice(1, 2)  # second char ("" if missing)

        # CW if:
        #  - starts with 'n' (your earlier rule)
        #  - OR second character is 'C' (new rule: YC means CW)
        is_cw = ch0.eq("n") | ch1.eq("C")

        # Pulse only if pulse enable 'Y' AND NOT CW
        is_pulse = ch0.eq("Y") & (~is_cw)

        df["Pmode"] = np.where(is_pulse, 1, 0).astype(int)
    else:
        df["Pmode"] = 0

    # Best-effort numeric conversion
    for c in df.columns:
        # Skip known text columns if you want (optional), otherwise best-effort convert
        if df[c].dtype == object:
            # Best-effort numeric conversion:
            # pandas in your env does NOT accept errors="ignore" for to_numeric.
            # Strategy: convert with errors="coerce", and only overwrite if most values are numeric.
            for c in df.columns:
                if df[c].dtype == object:
                    conv = pd.to_numeric(df[c], errors="coerce")
                    if conv.notna().mean() >= 0.6:  # >=60% numeric -> treat as numeric column
                        df[c] = conv

    # ----------------------------------------------------------
    # Delivered power: Pdel = Pfwd - Pref
    # ----------------------------------------------------------
    if "Pfwd" in df.columns and "Pref" in df.columns:
        pfwd = pd.to_numeric(df["Pfwd"], errors="coerce")
        pref = pd.to_numeric(df["Pref"], errors="coerce")
        df["Pdel"] = pfwd - pref

    return df
# =============================================================================
# ----------------------------- Header Parsing ---------------------------------
# =============================================================================

def parse_unit_info_from_header(lines: List[str]) -> Dict[str, str]:
    text = "".join(lines[:4000])
    info = {"FW": "", "FPGA": "", "SN": "", "UnitType": ""}

    m = re.search(r"Unit_SW_Type\s*,\s*([^\r\n]+)", text)
    if m:
        info["UnitType"] = m.group(1).strip()

    for ln in lines[:4000]:
        if ln.strip().startswith("Unit_Info"):
            parts = [p.strip() for p in ln.split(",")]
            for i in range(len(parts) - 1):
                if parts[i] in ("S/N", "SN", "S/N#"):
                    info["SN"] = parts[i + 1]
                if parts[i] in ("SW#", "SW"):
                    sw = parts[i + 1]
                    info["FW"] = sw.split(".")[-1] if "." in sw else sw
                if parts[i] in ("FPGA#", "FPGA"):
                    fp = parts[i + 1]
                    info["FPGA"] = fp.split(".")[-1] if "." in fp else fp
            break

    return info


def parse_time_info_from_header(lines: List[str]) -> Dict[str, Optional[str]]:
    """
    Best-effort parse of time-related header fields. Returns dict with optional keys:
      - 'host_time': ISO datetime string if found (e.g. '2026-03-23 20:36:17.552')
      - 'tlog_start_time': datetime string parsed from 'tlog start time : YYYYMMDD-HHMMSS'
    """
    out = {"host_time": None, "tlog_start_time": None}
    head = "".join(lines[:4000])
    # host time before tlog : 2026-03-23 20:36:17.552
    m = re.search(r'host time before tlog\s*:\s*([0-9\- :\.]+)', head, flags=re.IGNORECASE)
    if m:
        s = m.group(1).strip()
        # try parse with ms then without
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = _dt.datetime.strptime(s, fmt)
                out['host_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                break
            except Exception:
                continue

    m2 = re.search(r'tlog start time\s*:\s*(\d{8}-\d{6})', head, flags=re.IGNORECASE)
    if m2:
        s2 = m2.group(1).strip()
        try:
            dt2 = _dt.datetime.strptime(s2, "%Y%m%d-%H%M%S")
            out['tlog_start_time'] = dt2.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            out['tlog_start_time'] = None

    return out


def extract_parameter_blocks(lines: List[str]) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    current_section = "Header"

    for ln in lines:
        s = ln.rstrip("\n")

        # Tykon
        if re.match(r"^\s*//\s*General Parameters", s):
            current_section = "General Parameters"
            continue
        if re.match(r"^\s*//\s*Match Parameters", s):
            current_section = "Match Parameters"
            continue
        if re.match(r"^\s*//\s*Generator Parameters", s):
            current_section = "Generator Parameters"
            continue
        if re.match(r"^\s*//\s*PIDs", s):
            current_section = "PIDs"
            continue

        # Quantum
        if re.match(r"^\s*//\s*General_Params", s):
            current_section = "General Parameters"
            continue
        if re.match(r"^\s*//\s*HF Match Params", s):
            current_section = "HF Match Params"
            continue
        if re.match(r"^\s*//\s*LF Match Params", s):
            current_section = "LF Match Params"
            continue

        # stop at data header
        if "sec,_ms." in s and "Pls" in s and "Freq" in s:
            break

        if s.strip() and not s.strip().startswith("*** NOTE"):
            out.append((current_section, s.strip()))

    return out

def load_tlog(input_path: str) -> Tuple[pd.DataFrame, Dict[str, str], List[Tuple[str, str]]]:
    # with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
    #     lines = f.readlines()
    with open(input_path, 'r', encoding="utf-8", errors='ignore') as f:
        lines = f.readlines()

    # --- Task I-03: strip user-added timestamp prefix ---
    lines = _strip_timestamp_prefix(lines)

    # Use the FIRST header block for unit_info/params (good enough for double-download case)
    unit_info = parse_unit_info_from_header(lines)
    header_params = extract_parameter_blocks(lines)

    # Find ALL data headers (for double-download files)
    headers = _find_all_data_headers(lines)
    if not headers:
        candidates = [ln.strip() for ln in lines if "sec,_ms" in ln]
        raise ValueError(
            "Could not find data header line.\n"
            "Lines containing 'sec,_ms' (first 10):\n" + "\n".join(candidates[:10])
        )

    # Normalize header from the first segment
    _, header_tokens0, data_start0 = headers[0]
    header0 = _normalize_header(header_tokens0)

    # Parse each segment until the next header
    dfs = []
    for seg_i, (h_idx, h_tokens, d_start) in enumerate(headers, start=1):
        header_i = _normalize_header(h_tokens)

        # Since you said identical format, enforce it (prevents silent column misalignment)
        if header_i != header0:
            raise ValueError(
                f"Multiple headers detected but column formats differ at segment {seg_i} (line {h_idx}). "
                "Cannot safely concatenate."
            )

        # end at next header_idx, else EOF
        next_header_idx = headers[seg_i][0] if seg_i < len(headers) else None

        df_part = _parse_data_rows(lines, header0, d_start, data_end_idx=next_header_idx)
        if not df_part.empty:
            df_part["segment"] = seg_i  # mark segment ID
            dfs.append(df_part)

    if not dfs:
        raise ValueError("No data rows found after parsing all segments.")

    df = pd.concat(dfs, ignore_index=True)

    df = _derive_columns(df)

    # --- Time alignment (best-effort, non-destructive) ---
    try:
        time_info = parse_time_info_from_header(lines)
        host_time_str = time_info.get('host_time')
        tlog_start_time_str = time_info.get('tlog_start_time')

        offset_dt = None
        # Prefer host_time if available
        if host_time_str:
            try:
                host_dt = _dt.datetime.strptime(host_time_str, '%Y-%m-%d %H:%M:%S')
                # align host_dt to first observed commented tlog time if present
                offset_dt = host_dt
            except Exception:
                offset_dt = None

        # If we have tlog_start_time but not host_time, use that as date anchor
        if offset_dt is None and tlog_start_time_str:
            try:
                offset_dt = _dt.datetime.strptime(tlog_start_time_str, '%Y-%m-%d %H:%M:%S')
            except Exception:
                offset_dt = None

        # If we have an offset anchor and df contains plotting time, compute mapping for chart x-axis.
        if offset_dt is not None and 't(s)' in df.columns:
            t_plot = pd.to_numeric(df['t(s)'], errors='coerce').fillna(0).to_numpy()
            if len(t_plot) > 0:
                # Align anchor to first plotted point (chart time), not raw EVC uptime time(s).
                first_t = float(t_plot[0])
                last_t = float(t_plot[-1])
                base_dt = offset_dt - _dt.timedelta(seconds=first_t)
                start_dt = base_dt + _dt.timedelta(seconds=first_t)
                stop_dt = base_dt + _dt.timedelta(seconds=last_t)
                unit_info['tlog_time_base_iso'] = base_dt.strftime('%Y-%m-%d %H:%M:%S.%f')
                unit_info['tlog_time_offset_secs'] = str((base_dt - _dt.datetime(1970, 1, 1)).total_seconds())
                unit_info['tlog_real_start'] = start_dt.strftime('%Y-%m-%d %H:%M:%S')
                unit_info['tlog_real_stop'] = stop_dt.strftime('%Y-%m-%d %H:%M:%S')

    except Exception:
        pass  # fail-safe: do nothing

    return df, unit_info, header_params
