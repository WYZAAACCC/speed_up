import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()
old = """            ca.nucleate_bulk(T, bulk[0], bulk[1], bulk[2], dt,
                             c_l=ca.c_liq, m_L=ML)"""
new = """            # 形核用【热过冷】驱动（两例相同）=> 只让【生长】这一个因素变化
            ca.nucleate_bulk(T, bulk[0], bulk[1], bulk[2], dt)"""
assert old in s, "bulk call"
s = s.replace(old, new, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("nucleation -> thermal in both; only growth differs")