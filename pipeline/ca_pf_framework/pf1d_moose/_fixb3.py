import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose/drive_B3.py"
s = io.open(P, encoding="utf-8").read()
old = '''        txt = txt.replace("  l_tol = 1e-10", "  l_tol = 1e-10\\n  automatic_scaling = true", 1)
    txt = txt.replace("  automatic_scaling = true",
                      "  automatic_scaling = true\\n  compute_scaling_once = false", 1)'''
new = '''        txt = txt.replace(
            "  l_tol = 1e-10",
            "  l_tol = 1e-10\\n  automatic_scaling = true\\n  compute_scaling_once = false", 1)'''
assert old in s, "anchor"
s = s.replace(old, new, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched")