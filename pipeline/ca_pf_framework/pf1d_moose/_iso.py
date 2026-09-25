import io, sys, os, subprocess, re
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose")
import mk_phys3d as M3
H = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
BIN = "/root/moose/modules/phase_field/phase_field-opt"
ENV = dict(os.environ)
ENV["PATH"] = "/root/miniconda3/envs/moose/bin:" + ENV.get("PATH", "")
base = M3.make_input(8.0e-6, 1600, 3.0e-7, "2.0e-7", "2.04", 400, scaling=False)
base = base.replace("nl_abs_tol = 1e-9", "nl_abs_tol = 1e-16", 1)
variants = {
    "no_antitrap": base.replace("""  [antitrap]
    type = AntitrappingCurrent
    variable = w
    v = phi
    f_name = F_at
    coupled_variables = "c phi T"
  []
""", "", 1),
    "no_at_and_no_M_phi": base,
}
assert variants["no_antitrap"] != base, "antitrap block not found"
for tag, txt in variants.items():
    if tag == "no_at_and_no_M_phi":
        continue
    d = os.path.join(H, "iso_" + tag)
    if not os.path.isdir(d):
        os.makedirs(d)
    io.open(os.path.join(d, "p.i"), "w", encoding="utf-8").write(txt)
    r = subprocess.run([BIN, "-i", "p.i"], cwd=d, capture_output=True, text=True, timeout=1800, env=ENV)
    out = r.stdout + r.stderr
    io.open(os.path.join(d, "r.log"), "w", encoding="utf-8").write(out)
    print(tag, "rc", r.returncode, "n0", out.count(" 0 Nonlinear"), "n1", out.count("\n 1 Nonlinear"),
          "nan", out.count("NANORINF"))