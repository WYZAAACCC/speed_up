import io, re, html
s = io.open("/tmp/plapp.html", encoding="utf-8", errors="replace").read()
# strip math markup for readability: keep alttext of math
s = re.sub(r"<math[^>]*alttext=\"([^\"]*)\"[^>]*>.*?</math>", lambda m: " $"+html.unescape(m.group(1))+"$ ", s, flags=re.S)
s = re.sub(r"<script.*?</script>", "", s, flags=re.S)
s = re.sub(r"<style.*?</style>", "", s, flags=re.S)
s = re.sub(r"<[^>]+>", " ", s)
s = html.unescape(s)
s = re.sub(r"[ \t]+", " ", s)
out = []
for m in re.finditer(r"[Aa]nti-?trapping", s):
    a = max(0, m.start() - 1500); b = min(len(s), m.end() + 2500)
    out.append(s[a:b])
io.open("/tmp/plapp_at.txt", "w", encoding="utf-8").write("\n\n=========\n\n".join(out))
print("hits:", len(out), "chars:", sum(len(o) for o in out))