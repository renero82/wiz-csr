"""Wiz CSR - interfaccia grafica (Tkinter)."""
import os
import sys
import tempfile
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

import csr_core as core


def lines(widget: tk.Text) -> list:
    return [l.strip() for l in widget.get("1.0", "end").splitlines() if l.strip()]


COFFEE_URL = "https://buymeacoffee.com/renero82"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Wiz CSR")
        self.geometry("760x640")
        self.minsize(700, 600)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        self.v = {}

        self._tab_subject(nb)
        self._tab_key(nb)
        self._tab_san(nb)
        self._tab_ext(nb)

        out = ttk.LabelFrame(self, text="Salvataggio")
        out.pack(fill="x", padx=8, pady=8)
        out.columnconfigure(1, weight=1)
        self.v["out_dir"] = tk.StringVar(value=os.path.expanduser("~"))
        self.v["base"] = tk.StringVar()
        ttk.Label(out, text="Cartella:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(out, textvariable=self.v["out_dir"]).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(out, text="Sfoglia…", command=self.choose_dir).grid(row=0, column=2, padx=6)
        ttk.Label(out, text="Nome file:").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(out, textvariable=self.v["base"]).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(out, text="(vuoto = Common Name)").grid(row=1, column=2, padx=6)
        self.self_signed = tk.BooleanVar()
        self.v["days"] = tk.StringVar(value="365")
        ss = ttk.Frame(out)
        ss.grid(row=2, column=0, columnspan=3, sticky="w", padx=6, pady=4)
        ttk.Checkbutton(ss, text="Crea anche certificato autofirmato, validità (giorni):",
                        variable=self.self_signed).pack(side="left")
        ttk.Entry(ss, textvariable=self.v["days"], width=6).pack(side="left", padx=4)
        ttk.Label(out, text="Ogni generazione crea una sottocartella nome_data-ora con key, csr, crt e info.txt.",
                  foreground="gray").grid(row=3, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 4))
        ttk.Button(self, text="Genera", command=self.generate).pack(pady=(0, 8), ipadx=16, ipady=4)
        link = tk.Label(self, text="☕ Offrimi un caffè", fg="#0b6bcb", cursor="hand2")
        link.pack(pady=(0, 8))
        link.bind("<Button-1>", lambda e: webbrowser.open(COFFEE_URL))

    # ---- tab ----
    def _entry_rows(self, parent, rows):
        parent.columnconfigure(1, weight=1)
        for i, (key, label, hint) in enumerate(rows):
            self.v[key] = tk.StringVar()
            ttk.Label(parent, text=label).grid(row=i, column=0, sticky="w", padx=8, pady=5)
            ttk.Entry(parent, textvariable=self.v[key]).grid(row=i, column=1, sticky="ew", padx=8, pady=5)
            if hint:
                ttk.Label(parent, text=hint, foreground="gray").grid(row=i, column=2, padx=8)

    def _tab_subject(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text="Subject")
        self._entry_rows(f, [
            ("cn", "Common Name (CN)", "es. www.esempio.it"),
            ("o", "Organizzazione (O)", ""),
            ("ou", "Unità org. (OU)", ""),
            ("c", "Paese (C)", "2 lettere, es. IT"),
            ("st", "Provincia/Stato (ST)", ""),
            ("l", "Località (L)", ""),
            ("email", "Email", ""),
        ])

    def _tab_key(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text="Chiave")
        f.columnconfigure(1, weight=1)
        self.v["key_type"] = tk.StringVar(value="RSA 2048")
        self.v["hash"] = tk.StringVar(value="SHA-256")
        self.v["pass"] = tk.StringVar()
        self.v["pass2"] = tk.StringVar()
        ttk.Label(f, text="Algoritmo / dimensione").grid(row=0, column=0, sticky="w", padx=8, pady=5)
        ttk.Combobox(f, textvariable=self.v["key_type"], values=core.KEY_TYPES, state="readonly"
                     ).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(f, text="Hash di firma").grid(row=1, column=0, sticky="w", padx=8, pady=5)
        ttk.Combobox(f, textvariable=self.v["hash"], values=list(core.HASHES), state="readonly"
                     ).grid(row=1, column=1, sticky="w", padx=8)
        ttk.Label(f, text="(ignorato per Ed25519)", foreground="gray").grid(row=1, column=2)
        ttk.Label(f, text="Passphrase chiave").grid(row=2, column=0, sticky="w", padx=8, pady=5)
        ttk.Entry(f, textvariable=self.v["pass"], show="•").grid(row=2, column=1, sticky="ew", padx=8)
        ttk.Label(f, text="Conferma passphrase").grid(row=3, column=0, sticky="w", padx=8, pady=5)
        ttk.Entry(f, textvariable=self.v["pass2"], show="•").grid(row=3, column=1, sticky="ew", padx=8)
        ttk.Label(f, text="Lascia vuoto per una chiave non cifrata.", foreground="gray"
                  ).grid(row=4, column=1, sticky="w", padx=8)

    def _tab_san(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text="SAN")
        f.columnconfigure((0, 1), weight=1)
        self.san = {}
        for i, (key, label) in enumerate([("dns", "DNS"), ("ip", "Indirizzi IP"),
                                          ("email", "Email"), ("uri", "URI")]):
            r, c = divmod(i, 2)
            box = ttk.LabelFrame(f, text=f"{label} (uno per riga)")
            box.grid(row=r, column=c, sticky="nsew", padx=8, pady=8)
            f.rowconfigure(r, weight=1)
            self.san[key] = tk.Text(box, height=8, width=30)
            self.san[key].pack(fill="both", expand=True, padx=4, pady=4)

    def _tab_ext(self, nb):
        f = ttk.Frame(nb)
        nb.add(f, text="Estensioni")
        f.columnconfigure((0, 1), weight=1)
        ku = ttk.LabelFrame(f, text="Key Usage (critical)")
        ku.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.ku = {}
        for k, label in core.KEY_USAGES:
            self.ku[k] = tk.BooleanVar()
            ttk.Checkbutton(ku, text=label, variable=self.ku[k]).pack(anchor="w", padx=8)
        eku = ttk.LabelFrame(f, text="Extended Key Usage")
        eku.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        self.eku = {}
        for oid, label in core.EXT_KEY_USAGES:
            self.eku[oid] = tk.BooleanVar()
            ttk.Checkbutton(eku, text=label, variable=self.eku[oid]).pack(anchor="w", padx=8)
        bc = ttk.LabelFrame(f, text="Basic Constraints")
        bc.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        self.is_ca = tk.BooleanVar()
        self.v["pathlen"] = tk.StringVar()
        ttk.Checkbutton(bc, text="CA (certificato di autorità)", variable=self.is_ca).pack(anchor="w", padx=8)
        row = ttk.Frame(bc)
        row.pack(anchor="w", padx=8, pady=4)
        ttk.Label(row, text="Path length (vuoto = illimitata):").pack(side="left")
        ttk.Entry(row, textvariable=self.v["pathlen"], width=5).pack(side="left", padx=4)

    # ---- azioni ----
    def choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.v["out_dir"].get() or os.path.expanduser("~"),
                                    title="Cartella dove salvare chiave e CSR")
        if d:
            self.v["out_dir"].set(d)

    def collect(self) -> core.CsrParams:
        g = lambda k: self.v[k].get().strip()
        if self.v["pass"].get() != self.v["pass2"].get():
            raise ValueError("Le passphrase non coincidono.")
        pathlen = g("pathlen")
        if pathlen and not pathlen.isdigit():
            raise ValueError("Path length deve essere un numero intero.")
        days = g("days")
        if self.self_signed.get() and not days.isdigit():
            raise ValueError("La validità deve essere un numero di giorni.")
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
            messagebox.showerror("Errore", str(e))
            return
        self.config(cursor="")
        self.show_result(res)

    def show_result(self, res):
        w = tk.Toplevel(self)
        w.title("Fatto")
        w.geometry("660x460")
        ttk.Label(w, text=f"Salvato in: {res['folder']}", justify="left").pack(anchor="w", padx=8, pady=8)
        nb = ttk.Notebook(w)
        nb.pack(fill="both", expand=True, padx=8)
        pems = [("CSR", res["csr_pem"])] + ([("Certificato", res["crt_pem"])] if res["crt_pem"] else [])
        for title, pem in pems:
            t = tk.Text(nb, wrap="none")
            t.insert("1.0", pem)
            nb.add(t, text=title)
        def copy():
            self.clipboard_clear()
            self.clipboard_append(pems[nb.index("current")][1])
        ttk.Button(w, text="Copia", command=copy).pack(pady=8)


def selftest(report: str) -> int:
    """Costruisce la finestra e genera chiave+CSR+certificato; scrive l'esito in `report`."""
    lines_out, ok = [], True
    try:
        app = App()
        app.update()
        app.v["cn"].set("selftest.example")
        app.v["c"].set("IT")
        app.san["dns"].insert("1.0", "selftest.example\nwww.selftest.example")
        app.ku["digital_signature"].set(True)
        app.self_signed.set(True)
        with tempfile.TemporaryDirectory() as tmp:
            app.v["out_dir"].set(tmp)
            p = app.collect()
            res = core.generate_and_save(p, tmp, "")
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
