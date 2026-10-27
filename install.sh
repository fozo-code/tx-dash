#!/data/data/com.termux/files/usr/bin/bash
# tx-dash - device dashboard for Termux
# Install: pkg install curl -y && curl -fsSL https://raw.githubusercontent.com/fozo-code/tx-dash/main/install.sh | bash
REL="https://github.com/fozo-code/tx-dash/releases/latest/download"
SELF="https://raw.githubusercontent.com/fozo-code/tx-dash/main/install.sh"
DIR="$HOME/.txdash"

R=$'\e[38;5;196m'; N=$'\e[0m'
say() { printf "%s❯%s %s\n" "$R" "$N" "$*"; }

if [ ! -d /data/data/com.termux ]; then echo "tx-dash works on Termux only."; exit 1; fi

say "Installing tx-dash..."
pkg install -y python termux-api >/dev/null 2>&1

case "$(uname -m)" in
  aarch64|arm64) A=aarch64 ;;
  armv7l|armv8l|arm*) A=arm ;;
  x86_64) A=x86_64 ;;
  i686|i386) A=i686 ;;
  *) echo "Unsupported CPU: $(uname -m)"; exit 1 ;;
esac
PYV=$(python -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor}")')

mkdir -p "$DIR"
if ! curl -fsSL "$REL/txdash-py$PYV-$A" -o "$DIR/txdash-bin"; then
  say "No build found for Python $PYV on $A."
  say "Run:  pkg upgrade -y   then run the install command again."
  rm -rf "$DIR"; exit 1
fi
chmod +x "$DIR/txdash-bin"
echo "$SELF" > "$DIR/url"

if ! "$DIR/txdash-bin" -v >/dev/null 2>&1; then
  say "The downloaded build does not run on this device."
  say "Run:  pkg upgrade -y   then try again."
  rm -rf "$DIR"; exit 1
fi

cat > "$PREFIX/bin/txdash" <<'EOF_BIN'
#!/data/data/com.termux/files/usr/bin/bash
D="$HOME/.txdash"
case "$1" in
  uninstall)
    sed -i '/# >>> txdash >>>/,/# <<< txdash <<</d' "$HOME/.bashrc"
    rm -rf "$D" "$PREFIX/bin/txdash"
    echo "tx-dash removed." ;;
  update)
    curl -fsSL "$(cat "$D/url")" | bash ;;
  startup)
    sed -i '/# >>> txdash >>>/,/# <<< txdash <<</d' "$HOME/.bashrc"
    if [ "$2" = "on" ]; then
      printf '\n# >>> txdash >>>\n[[ $- == *i* ]] && txdash -c\n# <<< txdash <<<\n' >> "$HOME/.bashrc"
      echo "Compact dashboard will show when Termux opens."
    else
      echo "Startup line disabled."
    fi ;;
  *) exec "$D/txdash-bin" "$@" ;;
esac
EOF_BIN
chmod +x "$PREFIX/bin/txdash"

echo
say "Done. Run:  txdash   |   txdash -w   |   txdash startup on"
echo
