"""Privately store TypeSafe's key using EventMarketDB's existing key locations.

Run with venv/bin/python scripts/store_typesafe_key.py in an interactive terminal.
Only TYPESAFE_API_KEY changes. No API calls to TypeSafe or service restarts occur.
"""

import argparse
import base64
import getpass
import json
from pathlib import Path
import subprocess
import sys
import warnings

from dotenv import dotenv_values, set_key

KEY_NAME = 'TYPESAFE_API_KEY'
CONTEXT = 'kubernetes-admin@kubernetes'
NAMESPACES = ('processing', 'mcp-services')
SECRET_NAME = 'eventtrader-secrets'
ENV_PATH = Path(__file__).resolve().parents[1] / '.env'


class SetupError(RuntimeError):
    """A setup failure whose message contains no credential material."""


def _kubectl(action, namespace, payload=None):
    command = ['kubectl', '--context', CONTEXT, '--request-timeout=15s',
               action, 'secret', SECRET_NAME, '-n', namespace, '-o', 'json']
    if action == 'patch':
        command += ['--type=merge', '--patch-file=/dev/stdin']
    try:
        result = subprocess.run(command, input=payload, capture_output=True,
                                text=True, timeout=25)
    except (OSError, subprocess.TimeoutExpired):
        raise SetupError(f'Could not {action} {namespace}/{SECRET_NAME}; '
                         'check cluster access and rerun.') from None
    if result.returncode:
        # Errors may repeat request contents. Never print kubectl stdout/stderr.
        raise SetupError(f'Could not {action} {namespace}/{SECRET_NAME}; '
                         'check cluster access and rerun.')
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise SetupError(f'Unreadable cluster response for {namespace}.') from None


def store_key(key, env_path=ENV_PATH):
    if not key or any(c.isspace() for c in key):
        raise SetupError('Enter one nonempty API key without whitespace.')
    env_path = Path(env_path)
    if not env_path.is_file():
        raise SetupError('The existing project .env file was not found.')
    # Verify both destinations exist before changing any stored credential.
    for namespace in NAMESPACES:
        _kubectl('get', namespace)

    try:
        set_key(env_path, KEY_NAME, key, quote_mode='always')
        env_path.chmod(0o600)
        local_ok = dotenv_values(env_path).get(KEY_NAME) == key
    except OSError:
        raise SetupError('Could not save the local .env file.') from None
    if not local_ok:
        raise SetupError('The local key did not verify; cluster values were not changed.')
    print(f'Verified local storage: {env_path} (owner access only)')

    encoded = base64.b64encode(key.encode()).decode()
    payload = json.dumps({'data': {KEY_NAME: encoded}})
    for namespace in NAMESPACES:
        # stdin keeps the credential out of command arguments and shell history.
        _kubectl('patch', namespace, payload)
        stored = _kubectl('get', namespace).get('data', {}).get(KEY_NAME)
        if stored != encoded:
            raise SetupError(f'The stored key did not verify in {namespace}.')
        print(f'Verified cluster storage: {namespace}/{SECRET_NAME}')


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    if not sys.stdin.isatty():
        print('Run this command in your interactive terminal for a hidden key prompt.')
        return 1
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            key = getpass.getpass('TypeSafe API key (hidden): ')
        store_key(key)
    except getpass.GetPassWarning:
        print('A hidden prompt is unavailable; no key was saved.')
        return 1
    except (SetupError, KeyboardInterrupt, EOFError) as error:
        print(str(error) if isinstance(error, SetupError) else '\nCancelled.')
        print('Any locations already marked verified remain saved; rerunning is safe.')
        return 1
    print('Done. New local processes and newly started pods can load the key.')
    print('No services were restarted and no TypeSafe API request was made.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
