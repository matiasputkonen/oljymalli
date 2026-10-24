#!/usr/bin/env python3
"""Orchestrates the full update: fetch -> derived files -> panels -> analysis -> models -> hazard/signals/weights -> page.
Each step is isolated; a failing step keeps the previous outputs and is reported in data/status.json and on the page.
Usage: python pipeline/run_all.py [--no-fetch] [--full]"""
import os, sys, json, time, subprocess, datetime as dt, pandas as pd
ROOT = os.environ.get("OIL_ROOT", "/home/claude/oil"); os.environ["OIL_ROOT"] = ROOT; D = f"{ROOT}/data"; SC = f"{ROOT}/scripts"; PL = f"{ROOT}/pipeline"
NOFETCH = "--no-fetch" in sys.argv; FULL = "--full" in sys.argv
STATUS = {"started": str(dt.datetime.utcnow())[:19] + "Z", "steps": {}}
def run(name, cmd, timeout=1500):
    t0 = time.time(); print(f"\n=== {name} ===", flush=True)
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=os.environ.copy())
        tail = (r.stdout.strip().splitlines() or [""])[-1][:200]; ok = r.returncode == 0
        STATUS["steps"][name] = dict(ok=ok, secs=round(time.time() - t0, 1), tail=tail, err=(r.stderr.strip().splitlines() or [""])[-1][:200] if not ok else "")
        print(r.stdout[-1500:] if ok else (r.stdout[-800:] + "\n" + r.stderr[-1500:]), flush=True)
    except Exception as e:
        STATUS["steps"][name] = dict(ok=False, secs=round(time.time() - t0, 1), err=str(e)[:200]); print("EXC", e, flush=True)
    return STATUS["steps"][name]["ok"]
if not NOFETCH: run("fetch", [sys.executable, f"{PL}/fetch_daily.py"] + (["--full"] if FULL else []), timeout=2400)
run("refresh_daily_files", [sys.executable, f"{PL}/refresh_daily_files.py"])
run("build_panel", [sys.executable, f"{SC}/build_panel.py"])
run("long_panel", [sys.executable, f"{SC}/long_panel.py"])
run("analyze", [sys.executable, f"{SC}/analyze.py"])
run("build_page", [sys.executable, f"{SC}/build_page.py"])
run("extra_series", [sys.executable, f"{SC}/extra_series.py"])
run("curve_now", [sys.executable, f"{SC}/curve_now.py"])
run("model", [sys.executable, f"{SC}/model.py"])
run("models17", [sys.executable, f"{SC}/models17.py"])
run("models8", [sys.executable, f"{SC}/models8.py"])
run("hazard", [sys.executable, f"{SC}/hazard.py"])
run("daily_signals", [sys.executable, f"{SC}/daily_signals.py"])
run("weights", [sys.executable, f"{SC}/weights.py"])
run("models_prob", [sys.executable, f"{SC}/models_prob.py"], timeout=1200)
run("evaluate_log", [sys.executable, f"{SC}/evaluate_log.py"])
# ---- assemble page data, forecast log, html ----
pg = json.load(open(f"{D}/page_data.json"))
for key, fn in [("hz", "hazard.json"), ("ds", "daily_signals.json"), ("wts", "weights.json"), ("prob", "prob.json"), ("eval", "eval.json"), ("fetch", "status_fetch.json")]:
    try: pg[key] = json.load(open(f"{D}/{fn}"))
    except Exception as e: print("missing", fn, e)
STATUS["finished"] = str(dt.datetime.utcnow())[:19] + "Z"
# data freshness
fresh = {}
try:
    for lab, fn, col in [("WTI/Brent päivähinta (FRED)", f"{D}/raw/fred_WTI_d.csv", "date"), ("EIA viikkovarastot", f"{D}/raw/eia_WCESTUS1w.csv", "date"), ("Hormuz-transitit (PortWatch)", f"{D}/hormuz_daily.csv", "date"), ("CFTC COT", f"{D}/raw/cftc_wti_cot.csv", "date")]:
        d = pd.read_csv(fn); fresh[lab] = str(pd.to_datetime(d[col]).max().date())
    fresh["OVX"] = str(pd.read_csv(f"{D}/raw3/fred_OVX.csv").dropna().iloc[-1, 0]); fresh["GPR-päiväindeksi"] = pg["hz"]["signals"]["gpr_date"] if "hz" in pg else "–"
    fresh["Futuurikäyrä (Yahoo)"] = pg["hz"]["series"]["date"][-1] if "hz" in pg else "–"
    fresh["Optiot"] = json.load(open(f"{D}/raw4/yahoo_options_CL.json"))["date"] if os.path.exists(f"{D}/raw4/yahoo_options_CL.json") else "2026-10-22 (CME, manuaalinen)"
    fresh["EIA STEO"] = pg.get("d8", {}).get("steo_meta", {}).get("vintage", "–")
except Exception as e: print("fresh fail", e)
STATUS["fresh"] = fresh; pg["status"] = STATUS
# forecast log (one row per run, target, horizon) for later evaluation
try:
    rows = []; now = STATUS["finished"]
    for t in ["wti", "brent"]:
        md = pg["model"][t]; st = pg.get("d8", {}).get("stack", {}).get(t, {}).get("horizons", {}); w = pg.get("wts", {}).get(t, {}); vw = md.get("views", {})
        for f in md["forecast"]:
            h = str(f["h"]); rows.append(dict(run=now, target=t, h=f["h"], target_month=f["date"][:7], anchor=md["P0"], anchor_date=md.get("P0_day"), fv_now=md["fv_now"], model_median=f["median"], curve=f["curve"], comb=f["comb"], comb_base=f.get("comb_base"), view=f.get("view"), p25=f["p25"], p75=f["p75"], p05=f["p05"], p95=f["p95"],
                             stack_dossier=st.get(h, {}).get("stack"), stack_shrunk=w.get(h, {}).get("stack_shrunk_now"), steo=(f.get("steo") if f.get("steo") is not None else st.get(h, {}).get("steo")), hazard=pg.get("hz", {}).get("now", {}).get("CL" if t == "wti" else "BZ", {}).get("hazard"),
                             w_steo=vw.get("steo_weight"), w_view=vw.get("user_weight"), view_type=vw.get("user_type")))
    log = pd.DataFrame(rows); fn = f"{D}/forecast_log.csv"
    if os.path.exists(fn): old = pd.read_csv(fn); log = pd.concat([old, log], ignore_index=True)
    log.to_csv(fn, index=False); pg["forecast_log_tail"] = log[log.run == now].to_dict("records")
    # change since previous run
    prev_runs = sorted(set(log.run)); prev = prev_runs[-2] if len(prev_runs) > 1 else None
    if prev:
        a = log[log.run == now].set_index(["target", "h"]); b = log[log.run == prev].set_index(["target", "h"]); ch = {}
        for k in a.index:
            if k in b.index: ch[f"{k[0]}_{k[1]}"] = dict(comb=round(float(a.loc[k, "comb"] - b.loc[k, "comb"]), 1), stack=(round(float(a.loc[k, "stack_dossier"] - b.loc[k, "stack_dossier"]), 1) if pd.notna(a.loc[k, "stack_dossier"]) and pd.notna(b.loc[k, "stack_dossier"]) else None), anchor=round(float(a.loc[k, "anchor"] - b.loc[k, "anchor"]), 1))
        pg["change"] = dict(prev_run=prev, changes=ch)
except Exception as e: print("forecast log fail", e)
json.dump(pg, open(f"{D}/page_data.json", "w"), ensure_ascii=False, default=float); json.dump(STATUS, open(f"{D}/status.json", "w"), indent=1)
# html
tpl = open(f"{ROOT}/page/template.html", encoding="utf-8").read(); data = json.dumps(pg, ensure_ascii=False, default=float).replace("</script>", "<\\/script>")
html = tpl.replace("__DATA__", data); os.makedirs(f"{ROOT}/docs", exist_ok=True)
open(f"{ROOT}/page/oljymarkkina.html", "w", encoding="utf-8").write(html); open(f"{ROOT}/docs/index.html", "w", encoding="utf-8").write(html)
print("\nDONE", {k: v["ok"] for k, v in STATUS["steps"].items()}, "html bytes", len(html))
