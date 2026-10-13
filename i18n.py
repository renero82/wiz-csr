"""Traduzioni (italiano / inglese) e preferenza di lingua."""
import json
import locale
import os
import subprocess
import sys

LANGS = {"en": "English", "it": "Italiano"}
_current = "en"
_PREF = os.path.join(os.path.expanduser("~"), ".wiz-csr.json")

# chiave: (italiano, inglese)
S = {
    # schede
    "tab_subject": ("Subject", "Subject"),
    "tab_key": ("Chiave", "Key"),
    "tab_san": ("SAN", "SAN"),
    "tab_ext": ("Estensioni", "Extensions"),
    # subject
    "f_cn": ("Common Name (CN)", "Common Name (CN)"),
    "f_o": ("Organizzazione (O)", "Organization (O)"),
    "f_ou": ("Unità org. (OU)", "Organizational unit (OU)"),
    "f_c": ("Paese (C)", "Country (C)"),
    "f_st": ("Provincia/Stato (ST)", "State/Province (ST)"),
    "f_l": ("Località (L)", "Locality (L)"),
    "f_email": ("Email", "Email"),
    "h_cn": ("es. www.esempio.it", "e.g. www.example.com"),
    "h_c": ("2 lettere, es. IT", "2 letters, e.g. US"),
    # chiave
    "k_algo": ("Algoritmo / dimensione", "Algorithm / size"),
    "k_hash": ("Hash di firma", "Signature hash"),
    "k_hash_hint": ("(ignorato per Ed25519)", "(ignored for Ed25519)"),
    "k_pass": ("Passphrase chiave", "Key passphrase"),
    "k_pass2": ("Conferma passphrase", "Confirm passphrase"),
    "k_pass_hint": ("Lascia vuoto per una chiave non cifrata.", "Leave empty for an unencrypted key."),
    # SAN
    "san_box": ("{label} (uno per riga)", "{label} (one per line)"),
    "san_ip": ("Indirizzi IP", "IP addresses"),
    # estensioni
    "e_ku": ("Key Usage (critical)", "Key Usage (critical)"),
    "e_eku": ("Extended Key Usage", "Extended Key Usage"),
    "e_bc": ("Basic Constraints", "Basic Constraints"),
    "e_ca": ("CA (certificato di autorità)", "CA (certificate authority)"),
    "e_path": ("Path length (vuoto = illimitata):", "Path length (empty = unlimited):"),
    # salvataggio
    "o_box": ("Salvataggio", "Output"),
    "o_folder": ("Cartella:", "Folder:"),
    "o_browse": ("Sfoglia…", "Browse…"),
    "o_name": ("Nome file:", "File name:"),
    "o_name_hint": ("(vuoto = Common Name)", "(empty = Common Name)"),
    "o_self": ("Crea anche certificato autofirmato, validità (giorni):",
               "Also create a self-signed certificate, validity (days):"),
    "o_info": ("Ogni generazione crea una sottocartella nome_data-ora con key, csr, crt e info.txt.",
               "Each run creates a name_date-time subfolder with key, csr, crt and info.txt."),
    "o_pick": ("Cartella dove salvare chiave e CSR", "Folder where to save key and CSR"),
    "o_generate": ("Genera", "Generate"),
    "coffee": ("☕ Offrimi un caffè", "☕ Buy me a coffee"),
    "language": ("Lingua:", "Language:"),
    # risultato / errori
    "r_title": ("Fatto", "Done"),
    "r_saved": ("Salvato in: {folder}", "Saved in: {folder}"),
    "r_cert": ("Certificato", "Certificate"),
    "r_copy": ("Copia", "Copy"),
    "err_title": ("Errore", "Error"),
    "err_pass": ("Le passphrase non coincidono.", "The passphrases do not match."),
    "err_pathlen": ("Path length deve essere un numero intero.", "Path length must be a whole number."),
    "err_days": ("La validità deve essere un numero di giorni.", "Validity must be a number of days."),
    "err_validity": ("La validità deve essere di almeno 1 giorno.", "Validity must be at least 1 day."),
    "err_subject": ("Specifica almeno un campo del Subject (es. Common Name).",
                    "Fill in at least one Subject field (e.g. Common Name)."),
    "err_country": ("Il Country deve essere un codice di 2 lettere (es. IT).",
                    "Country must be a 2-letter code (e.g. US)."),
    "err_outdir": ("Scegli una cartella di destinazione valida.", "Choose a valid destination folder."),
    "err_keytype": ("Tipo di chiave non supportato: {kt}", "Unsupported key type: {kt}"),
    "err_value": ("Valore non valido: {e}", "Invalid value: {e}"),
    # info.txt
    "s_generated": ("Generato il", "Generated on"),
    "s_subject": ("Subject", "Subject"),
    "s_key": ("Chiave", "Key"),
    "s_hash": ("hash", "hash"),
    "s_enc": ("Chiave cifrata con passphrase", "Key encrypted with passphrase"),
    "s_yes": ("sì", "yes"),
    "s_no": ("no", "no"),
    "s_ca": ("CA: sì (path length: {pl})", "CA: yes (path length: {pl})"),
    "s_unlimited": ("illimitata", "unlimited"),
    "s_self": ("Autofirmato, validità: {d} giorni", "Self-signed, validity: {d} days"),
    "s_files": ("File", "Files"),
}


def set_lang(code: str):
    global _current
    _current = code if code in LANGS else "en"


def get_lang() -> str:
    return _current


def t(key: str, **kw) -> str:
    it, en = S[key]
    text = it if _current == "it" else en
    return text.format(**kw) if kw else text


def detect_system_lang() -> str:
    try:
        if sys.platform == "win32":
            import ctypes
            if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x10:
                return "it"
        elif sys.platform == "darwin":
            out = subprocess.run(["defaults", "read", "-g", "AppleLanguages"],
                                 capture_output=True, text=True, timeout=3).stdout
            first = [l.strip(' ",()') for l in out.splitlines() if l.strip(' ",()')]
            if first and first[0].lower().startswith("it"):
                return "it"
        else:
            if (os.environ.get("LANG") or locale.getlocale()[0] or "").lower().startswith("it"):
                return "it"
    except Exception:  # noqa: BLE001
        pass
    return "en"


def load_pref() -> str:
    try:
        with open(_PREF, encoding="utf-8") as f:
            code = json.load(f).get("lang")
            if code in LANGS:
                return code
    except Exception:  # noqa: BLE001
        pass
    return detect_system_lang()


def save_pref(code: str):
    try:
        with open(_PREF, "w", encoding="utf-8") as f:
            json.dump({"lang": code}, f)
    except OSError:
        pass
