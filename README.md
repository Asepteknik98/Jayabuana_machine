# XCMG SafeDig AI Copilot

SEE BELOW • DIG RIGHT • STAY ALERT

Engineering prototype / simulation / demonstration untuk excavator.

Tahap 0: scaffold minimum. Belum ada UI atau fitur modul.

Target: Windows 10/11, Python 3.11+, desktop PySide6.

Setup dependency:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Jalankan scaffold (hanya menampilkan pesan terminal):

```powershell
python main.py
```

Direktori utama: `config`, `core`, `modules`, `simulation`, `ui`,
`visualization`, `data`, `assets`, `services`, `models`, `output`, `tests`.
Direktori kosong disiapkan lokal; file ditambahkan sesuai tahap terkait.

GPR/EMI/GNSS dan machine telemetry pada demo nantinya merupakan simulated
input. Prototype tidak boleh mengendalikan excavator nyata. Automatic stop
atau restriction hanya simulated assistance output, belum tervalidasi
sebagai sistem functional-safety.
