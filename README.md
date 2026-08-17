# mpremote-sync

Verify and sync Python files to a MicroPython device via [mpremote](https://github.com/mpremote-org/mpremote).

Compare local SHA-256 hashes against files on the device. Auto-upload any that differ.

## Install

```bash
pip install mpremote-sync
```

## Usage

```bash
# Scan a directory and create the deploy list
mpremote-sync -d ./firmware --update

# Check files are in sync
mpremote-sync -d ./firmware

# Check and auto-upload mismatches
mpremote-sync -d ./firmware --fix
```

## Flags

```
mpremote-sync [-h] [-d DIR] [-l FILE] [-e PATTERN] [--fix] [--update] [--version]

  -d, --directory DIR   Source directory containing .py files (default: current directory)
  -l, --list FILE       Deploy list file path (default: .deploy_files)
  -e, --exclude PATTERN Glob pattern to exclude during --update (repeatable, default: *_template.py)
  --fix                 Auto-upload mismatched or missing files
  --update              Rescan source directory and update the deploy list
  --version             Show version
```

## Workflow

1. **Add new files** → `mpremote-sync -d ./firmware --update`
2. **Deploy** → `mpremote-sync -d ./firmware --fix`
3. **Daily** → `mpremote-sync -d ./firmware --fix`

## Requirements

- Python 3.13+
- [mpremote](https://github.com/mpremote-org/mpremote) installed and in PATH
