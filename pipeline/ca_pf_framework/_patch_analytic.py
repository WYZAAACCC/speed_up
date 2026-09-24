import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py"
s = io.open(P, encoding="utf-8").read()
if "capture_mode" in s:
    print("already patched"); raise SystemExit

# 1) __init__: 增加 capture 模式与 seeds 记录
s = s.replace(
    "        # 轴向周期边界（默认全关；开后在 _pair 里环绕）。",
    "        # capture: \"decentered\"（默认，历史/生产用的格点路径规则）\n"
    "        #          \"analytic\"（种子相对的【连续八面体】判据，去掉格点路径偏差）\n"
    "        self.capture = capture\n"
    "        self.seeds = [None]                     # seeds[gid] = (i,j,k) 种子位置\n"
    "        # 轴向周期边界（默认全关；开后在 _pair 里环绕）。", 1)
s = s.replace("                 periodic=(False, False, False)):",
              "                 periodic=(False, False, False), capture=\"decentered\"):", 1)

# 2) add_grain: 记录种子位置
s = s.replace("        self.axes.append(quat_to_axes(q))\n        self.gid[i, j, k] = g",
              "        self.axes.append(quat_to_axes(q))\n        self.seeds.append((i, j, k))\n"
              "        self.gid[i, j, k] = g", 1)

# 3) step: analytic 模式下用连续八面体判据替换 26 邻居循环
old_loop = "        for o, _ in OFFSETS:\n            pr = self._pair(o, window)\n            if pr is None:\n                continue\n            sx, tx = pr\n            gS = gid[sx]"
assert old_loop in s, "loop anchor"
new_loop = '''        if self.capture == "analytic":
            # ---- 连续八面体判据（种子相对）：去掉格点路径代价的取向偏差 ----
            # 到达判据:  support_g(x) = sum_a |p_a . (x - x_g)|  <=  L_g
            # 谁的比例 L_g / support_g 最大谁先到 => 直接比较该比例。
            X, Y, Z = self.coords()
            for g in range(1, len(self.axes)):
                sg = self.seeds[g]
                if sg is None:
                    continue
                Lg = float(self.L[sg[0], sg[1], sg[2]])
                if Lg <= 0.0:
                    continue
                Pg = self.axes[g]
                # 包围盒: support >= |d|  =>  只在 |d| <= Lg 内可能被捕获
                m = int(math.ceil(Lg / self.dx)) + 1
                i0g = max(window[0], sg[0] - m); i1g = min(window[1], sg[0] + m + 1)
                j0g = max(window[2], sg[1] - m); j1g = min(window[3], sg[1] + m + 1)
                k0g = max(window[4], sg[2] - m); k1g = min(window[5], sg[2] + m + 1)
                if i1g <= i0g or j1g <= j0g or k1g <= k0g:
                    continue
                dxv = (X[i0g:i1g, j0g:j1g, k0g:k1g] - X[sg[0], sg[1], sg[2]])
                dyv = (Y[i0g:i1g, j0g:j1g, k0g:k1g] - Y[sg[0], sg[1], sg[2]])
                dzv = (Z[i0g:i1g, j0g:j1g, k0g:k1g] - Z[sg[0], sg[1], sg[2]])
                sup = (np.abs(Pg[0, 0] * dxv + Pg[1, 0] * dyv + Pg[2, 0] * dzv) +
                       np.abs(Pg[0, 1] * dxv + Pg[1, 1] * dyv + Pg[2, 1] * dzv) +
                       np.abs(Pg[0, 2] * dxv + Pg[1, 2] * dyv + Pg[2, 2] * dzv))
                sub = (slice(i0g, i1g), slice(j0g, j1g), slice(k0g, k1g))
                free = gid[sub] == 0
                with np.errstate(divide="ignore", invalid="ignore"):
                    ratio = np.where(sup > 0, Lg / np.maximum(sup, 1e-300), -1.0)
                cand = free & (ratio >= 1.0)
                if not cand.any():
                    continue
                upd = cand & (ratio > best[sub])
                np.copyto(best[sub], np.where(upd, ratio, best[sub]))
                np.copyto(bsrc[sub], np.where(upd, np.int64(g), bsrc[sub]))
                np.copyto(bthr[sub], np.where(upd, sup, bthr[sub]))
        for o, _ in OFFSETS if self.capture == "decentered" else []:
            pr = self._pair(o, window)
            if pr is None:
                continue
            sx, tx = pr
            gS = gid[sx]'''
s = s.replace(old_loop, new_loop, 1)

# 4) 捕获后的 L 继承：analytic 模式下不需要（保持 0），避免误用
s = s.replace("            self.L.flat[ti] = np.maximum(self.L.flat[si] - bthr[cap], 0.0)",
              "            if self.capture == \"decentered\":\n"
              "                self.L.flat[ti] = np.maximum(self.L.flat[si] - bthr[cap], 0.0)\n"
              "            else:\n"
              "                self.L.flat[ti] = np.maximum(bthr[cap] * 0.0, 0.0)   # 未使用", 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched analytic capture")