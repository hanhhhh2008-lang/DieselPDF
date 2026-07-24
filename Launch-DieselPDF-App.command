#!/bin/zsh
set -e

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR"

if [[ -x .venv/bin/python ]]; then
  exec .venv/bin/python DieselPDF.pyw
fi

echo "DieselPDF has not been set up on this Mac yet."
echo "Run Setup-DieselPDF-macOS.command first."
read "REPLY?Press Return to close."
