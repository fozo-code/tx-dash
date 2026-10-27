# tx-dash

Device dashboard in a red box: battery, RAM, CPU, storage, network, uptime.
Works on **Termux (Android)** and **Windows (CMD / PowerShell)**.

## Install

**Termux**
```bash
pkg install curl -y && curl -fsSL https://raw.githubusercontent.com/fozo-code/tx-dash/main/install.sh | bash
```

**Windows (paste in CMD or PowerShell)**
```
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/fozo-code/tx-dash/main/install.ps1 | iex"
```
Python 3 is required on Windows (`winget install Python.Python.3.12`). Open a new terminal after installing.

## Use

```
txdash              show once
txdash -w           live view
txdash -c           one-line summary
txdash update
txdash uninstall
```

Termux only: `txdash startup on` shows the summary every time Termux opens. Battery temperature needs the Termux:API app.

## License

MIT
