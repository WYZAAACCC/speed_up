import io
p = "p1c_prod1d.py"
s = io.open(p, encoding="utf-8").read()

old = '''    tag = "A%g_W%g_kc%g" % (A, WF * 1e6, KC)
    d = os.path.join(HERE, "prod1d_" + tag)
    os.makedirs(d, exist_ok=True)'''
new = '''    tag = "A%g_W%g_kc%g" % (A, WF * 1e6, KC)
    suf = os.environ.get("PROD1D_SUFFIX", "")
    if suf:
        tag += "_" + suf
    d = os.path.join(HERE, "prod1d_" + tag)
    os.makedirs(d, exist_ok=True)
    # defensive: a reused directory would mix profile_line_<timestep>.csv from
    # earlier runs and max() would then read a STALE profile (AGENTS lesson #25).
    for f in os.listdir(d):
        if f.startswith("profile_line_") or f == "p1c_prod1d_out.csv":
            os.remove(os.path.join(d, f))'''
assert old in s, "anchor not found"
s = s.replace(old, new)
io.open(p, "w", encoding="utf-8").write(s)
print("patched p1c_prod1d.py ok")