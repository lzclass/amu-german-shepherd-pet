#!/usr/bin/env python3
"""Install the included Amu package using only the Python standard library."""
import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pets-dir', type=Path, help='Override the Codex pets directory.')
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / 'packages' / 'amu'
    manifest = json.loads((source / 'pet.json').read_text(encoding='utf-8'))
    version = json.loads((source / 'version.json').read_text(encoding='utf-8'))
    sprite = source / manifest['spritesheetPath']
    expected = version['sha256']
    if hashlib.sha256(sprite.read_bytes()).hexdigest() != expected:
        raise SystemExit('Package checksum mismatch; installation stopped.')
    codex_home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    pets = (args.pets_dir or codex_home / 'pets').expanduser().resolve()
    pets.mkdir(parents=True, exist_ok=True)
    target = pets / 'amu'
    names = ['pet.json', 'spritesheet.png', 'version.json']
    backup = None
    if target.is_symlink():
        raise SystemExit('Refusing to replace a symbolic-link installation.')
    if target.exists():
        if not target.is_dir():
            raise SystemExit('Installation target is not a directory.')
        if all((target / n).is_file() and (target / n).read_bytes() == (source / n).read_bytes() for n in names):
            print(f'Amu {version["version"]} is already installed: {target}')
            return
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = pets.parent / 'pet-backups' / f'amu-{stamp}'
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(target, backup)
    with tempfile.TemporaryDirectory(prefix='.amu-install-', dir=pets) as temp:
        stage = Path(temp) / 'amu'
        shutil.copytree(source, stage)
        if target.exists():
            for name in names:
                os.replace(stage / name, target / name)
        else:
            os.replace(stage, target)
    assert hashlib.sha256((target / manifest['spritesheetPath']).read_bytes()).hexdigest() == expected
    print(f'Installed Amu {version["version"]}: {target}')
    if backup:
        print(f'Previous installation backed up: {backup}')
    print('Open Settings > Pets, refresh the custom pets, and select Amu.')


if __name__ == '__main__':
    main()
