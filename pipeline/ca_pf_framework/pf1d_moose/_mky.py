import io
H = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
base = io.open(H + "/p1c_alpha2.i", encoding="utf-8").read()
oldk = """  [pin_b]
    type = CoupledForce
    variable = phi
    v = phi_targ
    coef = 1.0
  []"""
newk = """  [pin_b]
    type = BodyForce
    variable = phi
    function = phi_f
  []"""
assert oldk in base, "pin_b anchor"
base = base.replace(oldk, newk, 1)
extra = """  [phi_c]
    type = PointValue
    variable = phi
    point = "5.000000e-07 0 0"
  []
  [ptgt]
    type = PointValue
    variable = phi_targ
    point = "5.000000e-07 0 0"
  []
"""
s = base.replace("end_time = 1.4e-5", "end_time = 5.0e-7", 1)
s = s.replace("\n[]\n\n[Executioner]", "\n" + extra + "[]\n\n[Executioner]", 1)
assert extra in s
m1 = "[Mesh]\n  type = GeneratedMesh\n  dim = 1\n  nx = 1200\n  xmin = 0.0\n  xmax = 2.4e-6\n[]"
mA = "[Mesh]\n  type = GeneratedMesh\n  dim = 3\n  nx = 1200\n  ny = 1\n  nz = 1\n  xmin = 0.0\n  xmax = 2.4e-6\n  ymin = 0.0\n  ymax = 1.0e-6\n  zmin = 0.0\n  zmax = 1.0e-6\n[]"
assert m1 in s
io.open(H + "/y_1D.i", "w", encoding="utf-8").write(s)
io.open(H + "/y_3D.i", "w", encoding="utf-8").write(s.replace(m1, mA, 1))
print("ok")