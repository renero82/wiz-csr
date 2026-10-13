"""Apre l'app con dati di esempio e salva uno screenshot per ogni scheda in docs/ (usato in CI)."""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from PIL import Image, ImageGrab  # noqa: E402

import app as wiz  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "docs")
os.makedirs(OUT, exist_ok=True)


def grab(win, name):
    win.update_idletasks()
    win.update()
    x, y, w, h = win.winfo_rootx(), win.winfo_rooty(), win.winfo_width(), win.winfo_height()
    if sys.platform == "darwin":
        tmp = os.path.join(tempfile.gettempdir(), "wiz_full.png")
        subprocess.run(["screencapture", "-x", tmp], check=True)
        img = Image.open(tmp)
        scale = img.width / win.winfo_screenwidth()
        img = img.crop((int(x * scale), int(y * scale), int((x + w) * scale), int((y + h) * scale)))
    else:
        img = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
    img.save(os.path.join(OUT, name))


app = wiz.App(lang="en")
app.geometry("760x690+10+20")
app.lift()
app.attributes("-topmost", True)
app.update()
s = app.v
s["cn"].set("www.example.com")
s["o"].set("Example Ltd")
s["ou"].set("IT")
s["c"].set("US")
s["st"].set("California")
s["l"].set("San Francisco")
s["email"].set("admin@example.com")
s["base"].set("")
app.san["dns"].insert("1.0", "www.example.com\nexample.com\napi.example.com")
app.san["ip"].insert("1.0", "192.0.2.10")
app.ku["digital_signature"].set(True)
app.ku["key_encipherment"].set(True)
for oid in app.eku:
    if oid == wiz.core.EXT_KEY_USAGES[0][0]:
        app.eku[oid].set(True)
s["key_type"].set("RSA 3072")
app.self_signed.set(True)
nb = app.nb
prefix = "macos" if sys.platform == "darwin" else "windows"
for idx, name in enumerate(["subject", "key", "san", "extensions"]):
    nb.select(idx)
    grab(app, f"{prefix}-{name}.png")
app.destroy()
