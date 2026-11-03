#!/usr/bin/env python3
"""Install the included Amu package using only the Python standard library."""
import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

NAMES = ('pet.json', 'spritesheet.png', 'version.json')
SPRITESHEET = 'spritesheet.png'
SHA256_PATTERN = re.compile(r'[0-9a-fA-F]{64}')


def metadata_error(message):
    raise SystemExit(f'Invalid package metadata: {message}; installation stopped.')


def load_json_object(source, name):
    path = source / name
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as error:
        metadata_error(f'{name} cannot be read: {error}')
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        metadata_error(f'{name} is not valid JSON: {error.msg} (line {error.lineno}, column {error.colno})')
    if not isinstance(data, dict):
        metadata_error(f'{name} must contain a JSON object')
    return data


def load_manifest(source):
    manifest = load_json_object(source, 'pet.json')
    if manifest.get('spritesheetPath') != SPRITESHEET:
        metadata_error(f'pet.json spritesheetPath must be "{SPRITESHEET}" '
                       '(absolute paths, parent paths and other file names are not supported)')
    return manifest


def load_version(source):
    version = load_json_object(source, 'version.json')
    value = version.get('version')
    if not isinstance(value, str) or not value.strip():
        metadata_error('version.json version must be a non-empty string')
    digest = version.get('sha256')
    if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
        metadata_error('version.json sha256 must be a 64-character hexadecimal string')
    version['sha256'] = digest.lower()
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview the installation without creating or modifying any files.')
    parser.add_argument('--json', action='store_true',
                        help='With --dry-run, print the installation plan as a JSON object.')
    parser.add_argument('--pets-dir', type=Path, help='Override the Codex pets directory.')
    args = parser.parse_args()
    if args.json and not args.dry_run:
        parser.error('--json can only be used together with --dry-run')
    source = Path(__file__).resolve().parents[1] / 'packages' / 'amu'
    for name in NAMES:
        if not (source / name).is_file():
            raise SystemExit(f'Package file missing: {name}; installation stopped.')
    manifest = load_manifest(source)
    version = load_version(source)
    sprite = source / manifest['spritesheetPath']
    expected = version['sha256']
    if hashlib.sha256(sprite.read_bytes()).hexdigest() != expected:
        raise SystemExit('Package checksum mismatch; installation stopped.')
    codex_home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    pets = (args.pets_dir or codex_home / 'pets').expanduser().resolve()
    target = pets / 'amu'
    if target.is_symlink():
        raise SystemExit('Refusing to replace a symbolic-link installation.')
    if target.exists() and not target.is_dir():
        raise SystemExit('Installation target is not a directory.')
    up_to_date = target.is_dir() and all(
        (target / name).is_file() and (target / name).read_bytes() == (source / name).read_bytes()
        for name in NAMES
    )
    if args.dry_run:
        if up_to_date:
            action = 'up_to_date'
        elif target.exists():
            action = 'update'
        else:
            action = 'first_install'
        if args.json:
            print(json.dumps({
                'version': version['version'],
                'target': str(target),
                'action': action,
                'backup_dir': str(pets.parent / 'pet-backups') if action == 'update' else None,
                'dry_run': True,
            }))
            return
        print(f'Version: {version["version"]}')
        print(f'Target: {target}')
        if action == 'up_to_date':
            print('Plan: already installed; no files will be written.')
        elif action == 'update':
            print(f'Plan: update; the current installation will be backed up under {pets.parent / "pet-backups"}.')
        else:
            print('Plan: first install; the target directory will be created.')
        print('Dry run: no files were created or modified.')
        return
    if up_to_date:
        print(f'Amu {version["version"]} is already installed: {target}')
        return
    pets.mkdir(parents=True, exist_ok=True)
    backup = None
    if target.exists():
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = pets.parent / 'pet-backups' / f'amu-{stamp}'
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(target, backup)
    with tempfile.TemporaryDirectory(prefix='.amu-install-', dir=pets) as temp:
        stage = Path(temp) / 'amu'
        shutil.copytree(source, stage)
        if target.exists():
            for name in NAMES:
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
