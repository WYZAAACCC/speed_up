import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose/drive_B3.py"
s = io.open(P, encoding="utf-8").read()
a = "    txt = MP3.make_input(XM, NX, TE, WV, A, LN) if is3d else \\\n        MP.make_input(XM, NX, TE, WV, A, LN)"
b = ("    txt = MP3.make_input(XM, NX, TE, WV, A, LN, scaling=False) if is3d else \\\n"
     "        MP.make_input(XM, NX, TE, WV, A, LN)")
assert a in s, "call anchor"
s = s.replace(a, b, 1)
a2 = """    if not is3d:
        assert "  l_tol = 1e-10" in txt
        txt = txt.replace(
            "  l_tol = 1e-10",
            "  l_tol = 1e-10\\n  automatic_scaling = true\\n  compute_scaling_once = false", 1)"""
b2 = """    if not is3d:
        assert "  l_tol = 1e-10" in txt
        txt = txt.replace(
            "  l_tol = 1e-10",
            "  l_tol = 1e-10\\n  automatic_scaling = true\\n  compute_scaling_once = false", 1)
    else:
        # measured unscaled |R0| = 5.79e-14 -> rule nl_abs_tol ~ 1e-3|R0| ; NO automatic_scaling
        # (automatic_scaling on this algebraic-phi system produced NaN at step ~18)
        assert "nl_abs_tol = 1e-9" in txt
        txt = txt.replace("nl_abs_tol = 1e-9", "nl_abs_tol = 1e-16", 1)"""
assert a2 in s, "scaling anchor"
s = s.replace(a2, b2, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched drive_B3")