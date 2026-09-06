#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unprivileged, allowlisted Plasma controls with a detached rollback watchdog.

Only the current user's panel properties or two Plasma layout files are changed.
No command, path or JavaScript supplied by the UI is executed. Layout reset does
not change accounts, personal files, application settings or partitions.
"""
from contextlib import contextmanager
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import select
import stat
import subprocess
import sys
import time
import uuid

from private_files import write_private_text

LIMIT = 8 * 1024 * 1024
FIELDS = ('height', 'location', 'alignment', 'floating', 'hiding', 'lengthMode')
LAYOUT_FILES = ('plasma-org.kde.plasma.desktop-appletsrc', 'plasmashellrc')


def validate(values, existing=False):
    if not isinstance(values, dict) or set(values) != set(FIELDS):
        raise ValueError('Choose all six taskbar settings.')
    low, high = (1, 1024) if existing else (24, 120)
    if type(values['height']) is not int or not low <= values['height'] <= high:
        raise ValueError('Taskbar height must be between 24 and 120.')
    if type(values['floating']) is not bool:
        raise ValueError('Floating must be on or off.')
    for key, allowed in {
        'location': ('top', 'bottom', 'left', 'right'),
        'alignment': ('left', 'center', 'right'),
        'hiding': ('none', 'autohide', 'dodgewindows', 'windowsgobelow'),
        'lengthMode': ('fill', 'fit', 'custom'),
    }.items():
        if values[key] not in allowed:
            raise ValueError('Unsupported taskbar setting: ' + key)
    return dict(values)


def panel_id(value):
    if type(value) is not int or not 0 <= value < 2**31:
        raise ValueError('Select an existing taskbar.')
    return value


def panel_script(identifier, values):
    identifier = panel_id(identifier)
    values = validate(values, existing=True)
    return ('var p=panelById(%d); if(!p) throw Error("Taskbar is no longer available"); '
            'var v=%s; p.location=v.location; p.lengthMode=v.lengthMode; '
            'p.alignment=v.alignment; p.floating=v.floating; p.hiding=v.hiding; '
            'p.height=v.height; print("ok");'
            % (identifier, json.dumps(values, separators=(',', ':'))))


def run(argv):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=12, check=True)
    return result.stdout.strip()


def plasma(script):
    return run(['/usr/bin/qdbus6', 'org.kde.plasmashell', '/PlasmaShell',
                'org.kde.PlasmaShell.evaluateScript', script])


INVENTORY_SCRIPT = ('print(JSON.stringify(panels().map(function(p){'
              'var views=new ConfigFile("plasmashellrc","PlasmaViews"); '
              'var cfg=new ConfigFile(views); cfg.group="Panel "+p.id; '
              'var hiding=p.hiding; '
              'if(hiding==="none" && Number(cfg.readEntry("panelVisibility"))===3) hiding="windowsgobelow"; '
              'return {id:p.id,screen:p.screen,'
              'height:p.height,location:p.location,alignment:p.alignment,floating:p.floating,'
              'hiding:hiding,lengthMode:p.lengthMode};})));')


def inventory():
    # Plasma 6.3's getter reports WindowsGoBelow as "none"; its shared config
    # retains the actual enum. Reading that prevents a lossy undo of this mode.
    data = json.loads(plasma(INVENTORY_SCRIPT))
    if not isinstance(data, list) or len(data) > 32:
        raise ValueError('The desktop returned an unexpected taskbar list.')
    for item in data:
        panel_id(item['id'])
        validate({k: item[k] for k in FIELDS}, existing=True)
    return data


def apply_panel(identifier, values, allow_height_minimum=False):
    if plasma(panel_script(identifier, values)) != 'ok':
        raise RuntimeError('The desktop did not acknowledge the taskbar change.')
    actual = next((p for p in inventory() if p['id'] == identifier), None)
    if actual is None:
        raise RuntimeError('Taskbar disappeared while checking the change.')
    for key in FIELDS:
        if actual[key] == values[key]:
            continue
        if key == 'height' and allow_height_minimum and values[key] <= actual[key] <= 1024:
            continue  # Plasma enforces the minimum space required by widgets.
        raise RuntimeError('Taskbar did not retain the requested ' + key + '; recovering the previous settings.')
    return actual


def private_dir(path):
    """Reject linked or foreign path components before creating private state."""
    path = Path(path)
    if not path.is_absolute():
        raise ValueError('Desktop settings require an absolute user directory.')
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        try:
            current.mkdir(mode=0o700)
        except FileExistsError:
            pass
        info = current.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, os.getuid()):
            raise ValueError('Unsafe user-directory path.')
        if info.st_mode & 0o022 and not (info.st_uid == 0 and info.st_mode & stat.S_ISVTX):
            raise ValueError('User directory is writable by another account.')
    if path.stat().st_uid != os.getuid():
        raise ValueError('Desktop state must belong to this account.')
    os.chmod(path, 0o700)
    return path


def read_file(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1 or info.st_size > LIMIT:
            raise ValueError('Unsafe or unusually large desktop settings file.')
        return stream.read(LIMIT + 1)


class Controller:
    def __init__(self, state=None, config=None):
        self.state = private_dir(state or Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'dagric/desktop')
        self.config = Path(config or os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
        self.session = hashlib.sha256((os.environ.get('DBUS_SESSION_BUS_ADDRESS', '') +
            Path('/proc/sys/kernel/random/boot_id').read_text()).encode()).hexdigest()

    def read(self, name):
        value = read_file(self.state / name)
        return json.loads(value) if value is not None else None

    def write(self, name, value):
        encoded = json.dumps(value)
        if len(encoded.encode('utf-8')) > LIMIT:
            raise ValueError('Desktop backup exceeds the safe recovery size; no preview can be started.')
        write_private_text(self.state / name, encoded)

    @contextmanager
    def locked(self):
        fd = os.open(self.state / 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
                raise ValueError('Unsafe desktop lock.')
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def watchdog(self, token):
        rfd, wfd = os.pipe()
        try:
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'watch', token, str(wfd)],
                pass_fds=(wfd,), start_new_session=True, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.close(wfd); wfd = -1
            ready, _, _ = select.select([rfd], [], [], 3)
            if not ready or os.read(rfd, 1) != b'1':
                process.terminate()
                raise RuntimeError('Automatic undo could not start; no preview applied.')
        finally:
            os.close(rfd)
            if wfd != -1:
                os.close(wfd)

    def service(self, action):
        run(['/usr/bin/systemctl', '--user', action, 'plasma-plasmashell.service'])

    def layout_backup(self):
        private_dir(self.config)
        result = {}
        for name in LAYOUT_FILES:
            value = read_file(self.config / name)
            result[name] = None if value is None else base64.b64encode(value).decode('ascii')
        return result

    def layout_write(self, files):
        private_dir(self.config)
        if set(files) != set(LAYOUT_FILES):
            raise ValueError('Invalid desktop layout backup.')
        decoded = {}
        for name in LAYOUT_FILES:
            if files[name] is not None:
                decoded[name] = base64.b64decode(files[name], validate=True).decode('utf-8')
                if len(decoded[name].encode('utf-8')) > LIMIT:
                    raise ValueError('Desktop layout backup is too large.')
        for name in LAYOUT_FILES:
            read_file(self.config / name)  # Reject unsafe existing leaves.
            if files[name] is None:
                (self.config / name).unlink(missing_ok=True)
            else:
                write_private_text(self.config / name, decoded[name])

    def restore(self, entry):
        if entry['session'] != self.session:
            raise ValueError('This preview belongs to a previous desktop session. Its backup is preserved; no other session was changed.')
        if entry['kind'] == 'panel':
            apply_panel(entry['id'], entry['before'])
        elif entry['kind'] == 'layout':
            self.service('stop')
            try:
                self.layout_write(entry['before'])
            finally:
                self.service('start')
        else:
            raise ValueError('Invalid preview record.')

    def revert(self, entry):
        self.restore(entry)
        self.write('pending.json', None)

    def dispatch(self, action, payload=None):
        with self.locked():
            pending = self.read('pending.json')
            stale_message = None
            if pending and pending['session'] != self.session:
                # Panel IDs must never be applied across desktop sessions.
                # Keep the evidence, and offer explicit layout undo if possible.
                self.write('previous-session-' + uuid.uuid4().hex + '.json', pending)
                if pending.get('kind') == 'layout':
                    old_undo = self.read('layout-undo.json')
                    if old_undo:
                        self.write('previous-undo-' + uuid.uuid4().hex + '.json', old_undo)
                    self.write('layout-undo.json', pending)
                self.write('pending.json', None)
                pending = None
                stale_message = 'An unfinished preview from a previous desktop session was archived without changing this session. A layout backup, if present, can be restored with Undo last layout reset.'
            if pending and pending['session'] == self.session and time.monotonic() >= pending['deadline']:
                self.revert(pending); pending = None
            if action in ('keep', 'revert'):
                if not pending:
                    return {'message': 'There is no active preview.'}
                if pending['session'] != self.session:
                    raise ValueError('Preview is from another desktop session; its backup has been preserved.')
                if action == 'revert':
                    self.revert(pending)
                else:
                    if pending['kind'] == 'layout':
                        self.write('layout-undo.json', pending)
                    self.write('pending.json', None)
                return {'message': 'Changes kept.' if action == 'keep' else 'Previous settings restored.'}
            if action == 'query':
                return {'panels': inventory(), 'pending': bool(pending),
                        'seconds': max(0, int(pending['deadline'] - time.monotonic())) if pending else 0,
                        'canUndoLayout': bool(self.read('layout-undo.json')),
                        **({'message': stale_message} if stale_message else {})}
            if pending:
                raise ValueError('Keep or revert the current preview before changing anything else.')
            if action not in ('apply', 'reset-layout', 'undo-layout'):
                raise ValueError('Unknown desktop action.')
            entry = {'token': uuid.uuid4().hex, 'session': self.session, 'deadline': time.monotonic() + 60}
            if action == 'apply':
                if not isinstance(payload, dict) or set(payload) != {'id', 'values'}:
                    raise ValueError('Invalid taskbar request.')
                identifier = panel_id(payload['id']); values = validate(payload['values'])
                current = next((p for p in inventory() if p['id'] == identifier), None)
                if current is None:
                    raise ValueError('The selected taskbar no longer exists.')
                entry.update(kind='panel', id=identifier, before={k: current[k] for k in FIELDS})
            else:
                undo = self.read('layout-undo.json') if action == 'undo-layout' else None
                if action == 'undo-layout' and not undo:
                    raise ValueError('No desktop layout backup is available.')
                # Initial recovery record exists before even stopping Plasma.
                entry.update(kind='layout', before=self.layout_backup())
            try:
                self.write('pending.json', entry)
                self.watchdog(entry['token'])  # Must acknowledge before any settings change.
                if action == 'apply':
                    effective = apply_panel(identifier, values, allow_height_minimum=True)
                else:
                    self.service('stop')
                    # Replace the backup with Plasma's final flushed settings.
                    entry['before'] = self.layout_backup()
                    self.write('pending.json', entry)
                    self.layout_write(undo['before'] if undo else {n: None for n in LAYOUT_FILES})
                    self.service('start')
            except Exception:
                # Always try to recover; retain journal if recovery itself fails.
                self.revert(entry)
                raise
            result = {'pending': True, 'seconds': 60, 'message': 'Preview applied. Keep it, or previous settings return automatically in 60 seconds.'}
            if action == 'apply' and effective['height'] != values['height']:
                result['message'] = f"Your widgets need at least {effective['height']} pixels of taskbar thickness. This is a 60-second preview; keep or revert it."
            return result


def main():
    if os.geteuid() == 0:
        raise SystemExit('Desktop controls must run as the signed-in user, never root.')
    if len(sys.argv) == 4 and sys.argv[1] == 'watch':
        controller = Controller()
        os.write(int(sys.argv[3]), b'1'); os.close(int(sys.argv[3]))
        for _ in range(75):
            time.sleep(1)
            with controller.locked():
                pending = controller.read('pending.json')
                if not pending or pending['token'] != sys.argv[2]:
                    return
                if time.monotonic() >= pending['deadline']:
                    controller.revert(pending)
                    return
        return
    try:
        if len(sys.argv) != 2:
            raise ValueError('One desktop action is required.')
        raw = sys.stdin.read(4097)
        if len(raw) > 4096:
            raise ValueError('Taskbar request is too large.')
        payload = json.loads(raw) if raw.strip() else None
        result = Controller().dispatch(sys.argv[1], payload)
        print(json.dumps({'ok': True, **result}))
    except Exception as error:
        print(json.dumps({'ok': False, 'message': str(error)}))
        sys.exit(1)


if __name__ == '__main__':
    main()
