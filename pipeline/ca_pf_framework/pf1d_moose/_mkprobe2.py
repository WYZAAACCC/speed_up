import io, sys
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose")
import mk_quad3d as MQ3, mk_quad as MQ
H = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
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
for tag, txt in (("1D", MQ.make_input(8.0e-6, 1600, 5.0e-7, "2.0e-7", "2.04", 400, "smooth")),
                 ("3D", MQ3.make_input(8.0e-6, 1600, 5.0e-7, "2.0e-7", "2.04", 400, "smooth"))):
    s = txt.replace("\n[]\n\n[VectorPostprocessors]", "\n" + extra + "[]\n\n[VectorPostprocessors]", 1)
    assert extra in s, tag
    io.open(H + "/probe2_" + tag + ".i", "w", encoding="utf-8").write(s)
print("ok")