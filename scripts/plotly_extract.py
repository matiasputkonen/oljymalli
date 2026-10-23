#!/usr/bin/env python3
"""Extract plotly traces (name, x, y) from an HTML page that embeds Plotly JSON (handles bdata base64 arrays)."""
import re, json, base64, sys, numpy as np, pandas as pd

DT = {'i1': '<i1', 'u1': '<u1', 'i2': '<i2', 'u2': '<u2', 'i4': '<i4', 'u4': '<u4', 'f4': '<f4', 'f8': '<f8'}

def decode_arr(obj):
    if isinstance(obj, dict) and 'bdata' in obj:
        b = obj['bdata']
        raw = base64.b64decode(b + '=' * (-len(b) % 4))
        return np.frombuffer(raw, dtype=DT[obj['dtype']]).astype(float).tolist()
    return obj

def extract(html):
    out = []
    # find Plotly.newPlot( id, [traces], layout ...) or plotly json blocks
    for m in re.finditer(r'Plotly\.newPlot\(\s*"[^"]+"\s*,\s*', html):
        start = m.end()
        # parse the JSON array that follows using a bracket matcher
        depth = 0; i = start; in_str = False; esc = False
        while i < len(html):
            c = html[i]
            if in_str:
                if esc: esc = False
                elif c == '\\': esc = True
                elif c == '"': in_str = False
            else:
                if c == '"': in_str = True
                elif c == '[': depth += 1
                elif c == ']':
                    depth -= 1
                    if depth == 0: break
            i += 1
        try:
            traces = json.loads(html[start:i+1])
        except Exception as e:
            print('parse fail', e, file=sys.stderr); continue
        for t in traces:
            x = decode_arr(t.get('x')); y = decode_arr(t.get('y'))
            if x is None or y is None or len(x) != len(y): continue
            out.append((t.get('name', ''), x, y))
    return out

if __name__ == '__main__':
    html = open(sys.argv[1], encoding='utf-8', errors='ignore').read()
    for name, x, y in extract(html):
        ys = np.array(y, dtype=float)
        print(f"{name!r:40} n={len(x)} x0={str(x[0])[:10]} x1={str(x[-1])[:10]} std={np.nanstd(ys):.3g} last={ys[-3:]}")
