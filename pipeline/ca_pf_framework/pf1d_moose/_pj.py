import io, sys, os, subprocess
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose")
import mk_phys3d as M3
H = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
BIN = "/root/moose/modules/phase_field/phase_field-opt"
ENV = dict(os.environ)
ENV["PATH"] = "/root/miniconda3/envs/moose/bin:" + ENV.get("PATH", "")
s = M3.make_input(8.0e-6, 1600, 3.0e-7, "2.0e-7", "2.04", 400, scaling=False)
s = s.replace("solve_type = NEWTON", "solve_type = PJFNK", 1)
s = s.replace("nl_abs_tol = 1e-9", "nl_abs_tol = 1e-16", 1)
extra = """  [cmn]
    type = NodalExtremeValue
    variable = c
    value_type = min
  []
  [cmx]
    type = NodalExtremeValue
    variable = c
    value_type = max
  []
"""
s = s.replace("\n[]\n\n[VectorPostprocessors]", "\n" + extra + "[]\n\n[VectorPostprocessors]", 1)
assert "PJFNK" in s and "NodalExtremeValue" in s
d = os.path.join(H, "pj3D")
if not os.path.isdir(d):
    os.makedirs(d)
io.open(os.path.join(d, "p.i"), "w", encoding="utf-8").write(s)
r = subprocess.run([BIN, "-i", "p.i"], cwd=d, capture_output=True, text=True, timeout=1800, env=ENV)
out = r.stdout + r.stderr
io.open(os.path.join(d, "r.log"), "w", encoding="utf-8").write(out)
print("rc", r.returncode)
print("n0", out.count(" 0 Nonlinear"), "n1", out.count("\n 1 Nonlinear"))
p = os.path.join(d, "p_out.csv")
print("csv:", io.open(p, encoding="utf-8").read().strip().splitlines()[-1] if os.path.exists(p) else "none")
for l in out.splitlines():
    if "NANORINF" in l or "ERROR" in l:
        print("MSG:", l.strip()[:110]); break