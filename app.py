"""Wiz CSR - interfaccia grafica (Tkinter)."""
import os
import sys
import tempfile
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

import csr_core as core
import i18n
from i18n import t

COFFEE_URL = "https://buymeacoffee.com/renero82"


def lines(widget: tk.Text) -> list:
    return [l.strip() for l in widget.get("1.0", "end").splitlines() if l.strip()]


class App(tk.Tk):
    def __init__(self, lang=None):
        super().__init__()
        i18n.set_lang(lang or i18n.load_pref())
        self.title("Wiz CSR")
        self.geometry("760x690")
        self.minsize(700, 650)
        self.state_cache = None
        self.frame = None
        self._build()

    # ---- costruzione UI ----
    def _build(self):
        self.frame = ttk.Frame(self)
        self.frame.pack(fill="both", expand=True)
        self.v = {}

        top = ttk.Frame(self.frame)
        top.pack(fill="x", padx=8, pady=(6, 0))
        self.lang_var = tk.StringVar(value=i18n.LANGS[i18n.get_lang()])
        lang = ttk.Combobox(top, textvariable=self.lang_var, values=list(i18n.LANGS.values()),
                            state="readonly", width=10)
        lang.pack(side="right")
        lang.bind("<<ComboboxSelected>>", self._on_lang)
        ttk.Label(top, text=t("language")).pack(side="right", padx=6)

        self.nb = ttk.Notebook(self.frame)
        self.nb.pack(fill="both", expand=True, padx=8, pady=(6, 0))
        self._tab_subject(self.nb)
        self._tab_key(self.nb)
        self._tab_san(self.nb)
        self._tab_ext(self.nb)

        out = ttk.LabelFrame(self.frame, text=t("o_box"))
        out.pack(fill="x", padx=8, pady=8)
        out.columnconfigure(1, weight=1)
        self.v["out_dir"] = tk.StringVar(value=os.path.expanduser("~"))
        self.v["base"] = tk.StringVar()
        ttk.Label(out, text=t("o_folder")).grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(out, textvariable=self.v["out_dir"]).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(out, text=t("o_browse"), command=self.choose_dir).grid(row=0, column=2, padx=6)
        ttk.Label(out, text=t("o_name")).grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(out, textvariable=self.v["base"]).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(out, text=t("o_name_hint")).grid(row=1, column=2, padx=6)
        self.self_signed = tk.BooleanVar()
        self.v["days"] = tk.StringVar(value="365")
        ss = ttk.Frame(out)
        ss.grid(row=2, column=0, columnspan=3, sticky="w", padx=6, pady=4)
        ttk.Checkbutton(ss, text=t("o_self"), variable=self.self_signed).pack(side="left")
        ttk.Entry(ss, textvariable=self.v["days"], width=6).pack(side="left", padx=4)
        ttk.Label(out, text=t("o_info"), foreground="gray"
                  ).grid(row=3, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 4))
        ttk.Button(self.frame, text=t("o_generate"), command=self.generate).pack(pady=(0, 8), ipadx=16, ipady=4)
        link = tk.Label(self.frame, text=t("coffee"), fg="#0b6bcb", cursor="hand2")
        link.pack(pady=(0, 8))
        link.bind("<Button-1>", lambda e: webbrowser.open(COFFEE_URL))

    def _on_lang(self, _event=None):
        code = next(c for c, name in i18n.LANGS.items() if name == self.lang_var.get())
        if code == i18n.get_lang():
            return
        state = self._get_state()
        self.frame.destroy()
        i18n.set_lang(code)
        i18n.save_pref(code)
        self._build()
        self._set_state(state)

    def _get_state(self):
        return {
            "v": {k: var.get() for k, var in self.v.items()},
            "san": {k: w.get("1.0", "end-1c") for k, w in self.san.items()},
            "ku": {k: var.get() for k, var in self.ku.items()},
            "eku": {k: var.get() for k, var in self.eku.items()},
            "is_ca": self.is_ca.get(), "self_signed": self.self_signed.get(),
            "tab": self.nb.index("current"),
        }

    def _set_state(self, st):
        for k, val in st["v"].items():
            self.v[k].set(val)
        for k, val in st["san"].items():
            self.san[k].insert("1.0", val)
        for k, val in st["ku"].items():
            self.ku[k].set(val)
        for k, val in st["eku"].items():
            self.eku[k].set(val)
        self.is_ca.set(st["is_ca"])
        self.self_signed.set(st["self_signed"])
        self.nb.select(st["tab"])

    # ---- tab ----
    def _entry_rows(self, parent, rows):
        parent.columnconfigure(1, weight=1)
        for i, (key, hint) in enumerate(rows):
            self.v[key] = tk.StringVar()
            ttk.Label(parent, text=t("f_" + key)).grid(row=i, column=0, sticky="w", padx=8, pady=5)
            ttk.Entry(parent, textvariable=self.v[key]).grid(row=i, column=1, sticky="ew", padx=8, pady=5)
            if hint:
                ttk.Label(parent, text=t(hint), foreground="gray").grid(row=i, column=2, padx=8)

    def _tab_subject(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text=t("tab_subject"))
        self._entry_rows(f, [("cn", "h_cn"), ("o", None), ("ou", None), ("c", "h_c"),
                             ("st", None), ("l", None), ("email", None)])

    def _tab_key(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text=t("tab_key"))
        f.columnconfigure(1, weight=1)
        self.v["key_type"] = tk.StringVar(value="RSA 2048")
        self.v["hash"] = tk.StringVar(value="SHA-256")
        self.v["pass"] = tk.StringVar()
        self.v["pass2"] = tk.StringVar()
        ttk.Label(f, text=t("k_algo")).grid(row=0, column=0, sticky="w", padx=8, pady=5)
        ttk.Combobox(f, textvariable=self.v["key_type"], values=core.KEY_TYPES, state="readonly"
                     ).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(f, text=t("k_hash")).grid(row=1, column=0, sticky="w", padx=8, pady=5)
        ttk.Combobox(f, textvariable=self.v["hash"], values=list(core.HASHES), state="readonly"
                     ).grid(row=1, column=1, sticky="w", padx=8)
        ttk.Label(f, text=t("k_hash_hint"), foreground="gray").grid(row=1, column=2)
        ttk.Label(f, text=t("k_pass")).grid(row=2, column=0, sticky="w", padx=8, pady=5)
        ttk.Entry(f, textvariable=self.v["pass"], show="•").grid(row=2, column=1, sticky="ew", padx=8)
        ttk.Label(f, text=t("k_pass2")).grid(row=3, column=0, sticky="w", padx=8, pady=5)
        ttk.Entry(f, textvariable=self.v["pass2"], show="•").grid(row=3, column=1, sticky="ew", padx=8)
        ttk.Label(f, text=t("k_pass_hint"), foreground="gray").grid(row=4, column=1, sticky="w", padx=8)

    def _tab_san(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text=t("tab_san"))
        f.columnconfigure((0, 1), weight=1)
        self.san = {}
        for i, (key, label) in enumerate([("dns", "DNS"), ("ip", t("san_ip")),
                                          ("email", "Email"), ("uri", "URI")]):
            r, c = divmod(i, 2)
            box = ttk.LabelFrame(f, text=t("san_box", label=label))
            box.grid(row=r, column=c, sticky="nsew", padx=8, pady=8)
            f.rowconfigure(r, weight=1)
            self.san[key] = tk.Text(box, height=8, width=30)
            self.san[key].pack(fill="both", expand=True, padx=4, pady=4)

    def _tab_ext(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text=t("tab_ext"))
        f.columnconfigure((0, 1), weight=1)
        ku = ttk.LabelFrame(f, text=t("e_ku"))
        ku.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.ku = {}
        for k, label in core.KEY_USAGES:
            self.ku[k] = tk.BooleanVar()
            ttk.Checkbutton(ku, text=label, variable=self.ku[k]).pack(anchor="w", padx=8)
        eku = ttk.LabelFrame(f, text=t("e_eku"))
        eku.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        self.eku = {}
        for oid, label in core.EXT_KEY_USAGES:
            self.eku[oid] = tk.BooleanVar()
            ttk.Checkbutton(eku, text=label, variable=self.eku[oid]).pack(anchor="w", padx=8)
        bc = ttk.LabelFrame(f, text=t("e_bc"))
        bc.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        self.is_ca = tk.BooleanVar()
        self.v["pathlen"] = tk.StringVar()
        ttk.Checkbutton(bc, text=t("e_ca"), variable=self.is_ca).pack(anchor="w", padx=8)
        row = ttk.Frame(bc)
        row.pack(anchor="w", padx=8, pady=4)
        ttk.Label(row, text=t("e_path")).pack(side="left")
        ttk.Entry(row, textvariable=self.v["pathlen"], width=5).pack(side="left", padx=4)

    # ---- azioni ----
    def choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.v["out_dir"].get() or os.path.expanduser("~"),
                                    title=t("o_pick"))
        if d:
            self.v["out_dir"].set(d)

    def collect(self) -> core.CsrParams:
        g = lambda k: self.v[k].get().strip()  # noqa: E731
        if self.v["pass"].get() != self.v["pass2"].get():
            raise ValueError(t("err_pass"))
        pathlen = g("pathlen")
        if pathlen and not pathlen.isdigit():
            raise ValueError(t("err_pathlen"))
        days = g("days")
        if self.self_signed.get() and not days.isdigit():
            raise ValueError(t("err_days"))
        return core.CsrParams(
            common_name=g("cn"), organization=g("o"), org_unit=g("ou"), country=g("c"),
            state=g("st"), locality=g("l"), email=g("email"),
            key_type=self.v["key_type"].get(), hash_name=self.v["hash"].get(),
            passphrase=self.v["pass"].get(),
            san_dns=lines(self.san["dns"]), san_ip=lines(self.san["ip"]),
            san_email=lines(self.san["email"]), san_uri=lines(self.san["uri"]),
            key_usages=[k for k, var in self.ku.items() if var.get()],
            ext_key_usages=[o for o, var in self.eku.items() if var.get()],
            is_ca=self.is_ca.get(), path_length=int(pathlen) if pathlen else None,
            self_signed=self.self_signed.get(), validity_days=int(days) if days.isdigit() else 365,
        )

    def generate(self):
        try:
            p = self.collect()
            self.config(cursor="watch")
            self.update_idletasks()
            res = core.generate_and_save(p, self.v["out_dir"].get(), self.v["base"].get())
        except Exception as e:
            self.config(cursor="")
            messagebox.showerror(t("err_title"), str(e))
            return
        self.config(cursor="")
        self.show_result(res)

    def show_result(self, res):
        w = tk.Toplevel(self)
        w.title(t("r_title"))
        w.geometry("660x460")
        ttk.Label(w, text=t("r_saved", folder=res["folder"]), justify="left").pack(anchor="w", padx=8, pady=8)
        nb = ttk.Notebook(w)
        nb.pack(fill="both", expand=True, padx=8)
        pems = [("CSR", res["csr_pem"])] + ([(t("r_cert"), res["crt_pem"])] if res["crt_pem"] else [])
        for title, pem in pems:
            box = tk.Text(nb, wrap="none")
            box.insert("1.0", pem)
            nb.add(box, text=title)

        def copy():
            self.clipboard_clear()
            self.clipboard_append(pems[nb.index("current")][1])
        ttk.Button(w, text=t("r_copy"), command=copy).pack(pady=8)


def selftest(report: str) -> int:
    """Costruisce la finestra (in entrambe le lingue) e genera chiave+CSR+certificato."""
    lines_out, ok = [], True
    try:
        app = App(lang="en")
        app.update()
        app.v["cn"].set("selftest.example")
        app.v["c"].set("IT")
        app.san["dns"].insert("1.0", "selftest.example\nwww.selftest.example")
        app.ku["digital_signature"].set(True)
        app.self_signed.set(True)
        app.lang_var.set("Italiano")      # prova il cambio lingua conservando i dati
        app._on_lang()
        app.update()
        assert i18n.get_lang() == "it" and app.v["cn"].get() == "selftest.example"
        with tempfile.TemporaryDirectory() as tmp:
            app.v["out_dir"].set(tmp)
            res = core.generate_and_save(app.collect(), tmp, "")
            for k in ("key", "csr", "crt"):
                assert os.path.getsize(res[k]) > 0, k
            lines_out.append("files: " + ", ".join(sorted(os.listdir(res["folder"]))))
        app.destroy()
        lines_out.append("selftest OK")
    except Exception as e:  # noqa: BLE001
        ok = False
        lines_out.append(f"selftest FAILED: {e!r}")
    with open(report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out) + "\n")
    return 0 if ok else 1


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--selftest":
        return selftest(sys.argv[2])
    App().mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
