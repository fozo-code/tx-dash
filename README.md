# tx-dash

Device dashboard for Termux: battery, RAM, CPU, storage, network, uptime, in a red box that fits a phone screen.

## Install

```bash
pkg install curl -y && curl -fsSL https://raw.githubusercontent.com/fozo-code/tx-dash/main/install.sh | bash
```

## Use

```bash
txdash              # show once
txdash -w           # live view (refresh every 1.5s)
txdash -c           # one-line summary
txdash startup on   # show the summary every time Termux opens
txdash startup off
txdash update
txdash uninstall
```

Battery temperature needs the Termux:API app (from F-Droid). Without it, battery % still works.
