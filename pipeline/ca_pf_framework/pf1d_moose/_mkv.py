import io, sys
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose")
import mk_quad as MQ
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
base = MQ.make_input(8.0e-6, 1600, 5.0e-7, "2.0e-7", "2.04", 400, "smooth")
variants = {
    "d3_1cell": ("[Mesh]\n  type = GeneratedMesh\n  dim = 1\n  nx = 1600\n  xmin = 0.0\n  xmax = 8.0000e-06\n[]",
                 "[Mesh]\n  type = GeneratedMesh\n  dim = 3\n  nx = 1600\n  ny = 1\n  nz = 1\n  xmin = 0.0\n  xmax = 8.0000e-06\n  ymin = 0.0\n  ymax = 5.0000e-07\n  zmin = 0.0\n  zmax = 5.0000e-07\n[]"),
    "d2_3cells": ("[Mesh]\n  type = GeneratedMesh\n  dim = 1\n  nx = 1600\n  xmin = 0.0\n  xmax = 8.0000e-06\n[]",
                  "[Mesh]\n  type = GeneratedMesh\n  dim = 2\n  nx = 1600\n  ny = 3\n  xmin = 0.0\n  xmax = 8.0000e-06\n  ymin = 0.0\n  ymax = 6.0000e-07\n[]"),
}
for tag, (a, b) in variants.items():
    assert a in base, tag
    io.open(H + "/v_" + tag + ".i", "w", encoding="utf-8").write(base.replace(a, b, 1))
print("ok")