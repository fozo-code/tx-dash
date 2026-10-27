#!/data/data/com.termux/files/usr/bin/bash
# tx-dash - device dashboard for Termux
# Install: pkg install curl -y && curl -fsSL https://raw.githubusercontent.com/fozo-code/tx-dash/main/install.sh | bash
RAW="https://raw.githubusercontent.com/fozo-code/tx-dash/main"
DIR="$HOME/.txdash"

R=$'\e[38;5;196m'; N=$'\e[0m'
say() { printf "%s❯%s %s\n" "$R" "$N" "$*"; }

if [ ! -d /data/data/com.termux ]; then echo "tx-dash works on Termux only."; exit 1; fi

say "Installing tx-dash..."
pkg install -y python termux-api >/dev/null 2>&1
mkdir -p "$DIR"
if ! curl -fsSL "$RAW/txdash.py" -o "$DIR/txdash.py"; then
  echo "Download failed. Check your connection."; exit 1
fi
echo "$RAW/install.sh" > "$DIR/url"

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
  *) exec python "$D/txdash.py" "$@" ;;
esac
EOF_BIN
chmod +x "$PREFIX/bin/txdash"

echo
say "Done. Run:  txdash        (once)"
say "           txdash -w     (live)"
say "           txdash startup on"
echo
if ! command -v termux-battery-status >/dev/null 2>&1 || ! timeout 3 termux-battery-status >/dev/null 2>&1; then
  say "Battery temperature needs the Termux:API app (F-Droid). Without it, battery % still works."
fi
echo
