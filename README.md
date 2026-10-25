# 🦥 sloth-tidy

A lazy file tidier that runs a local open-weight model. Point it at a messy folder (Downloads, say); it sorts and renames everything. Your files never leave your machine.

- Dry run by default. Nothing moves until you pass `--apply`
- One-command undo (`--undo`)
- Never overwrites a file
- Falls back to extension-based sorting if the model isn't running
- Zero dependencies: Python 3 standard library only

## Setup
1. Install [Ollama](https://ollama.com) and run `ollama pull llama3.2:3b` (any Ollama model works via `--model`)
2. `python3 sloth_tidy.py ~/Downloads` to preview
3. `python3 sloth_tidy.py ~/Downloads --apply` to do it
4. `python3 sloth_tidy.py ~/Downloads --undo` to revert

## Options
`--model NAME` · `--apply` · `--undo` · `--no-llm`

License: MIT
