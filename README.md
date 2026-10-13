# Wiz CSR

App portabile (Windows / macOS) per generare chiave privata + CSR scegliendo tutti i parametri.

## Esecuzione da sorgente
    pip install cryptography
    python app.py

## Build portabile (da lanciare sul sistema di destinazione)
    pip install -r requirements.txt
    pyinstaller --noconsole --onefile --windowed --name WizCSR app.py

- Windows: `dist/WizCSR.exe`
- macOS: `dist/WizCSR.app` (al primo avvio: tasto destro > Apri, perché non è firmata)

In alternativa usa la GitHub Action in `.github/workflows/build.yml` per costruire entrambe.

## Parametri
Subject (CN, O, OU, C, ST, L, email), algoritmo (RSA 2048/3072/4096, EC P-256/384/521, Ed25519),
hash, passphrase della chiave, SAN (DNS, IP, email, URI), Key Usage, Extended Key Usage, Basic Constraints.
Cartella di salvataggio e nome file scelti dall'utente; la chiave è scritta con permessi 0600.
