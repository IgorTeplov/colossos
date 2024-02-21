from sys import argv
from os import system
from pathlib import Path
from argparse import ArgumentParser
from cfex import CFEX
from time import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from watchdog.events import DirModifiedEvent, DirCreatedEvent, DirDeletedEvent, DirMovedEvent


def call(cmd, file=Path('temp')):
    system(f'{cmd} > temp')
    return file.read_text()

class SSH:
    def __init__(self, configs):
        self.key = configs['SSH_KEY']
        self.user = configs['SSH_USER']
        self.host = configs['SSH_HOST']

        self.local_dir = Path(configs['LOCAL_DIR'].replace('~', str(Path.home())))
        self.remote_dir = Path(configs['REMOTE_DIR'])
        self.local_store = self.local_dir / self.remote_dir.name

    def check(self):
        answer = call(f'ssh -i {self.key} {self.user}@{self.host} "ls {self.remote_dir.parent}"')
        return self.remote_dir.name in answer

    def download(self, path, r=False):
        r_flag = '-r' if r else ''
        call(f'scp -i {self.key} {r_flag} {self.user}@{self.host}:{path} {self.local_dir}')

    def upload(self, _from, _to):
        call(f'scp -i {self.key} {_from} {self.user}@{self.host}:{_to}')

    def create_file(self, _to):
        call(f'ssh -i {self.key} {self.user}@{self.host} "touch {_to}"')

    def create_dir(self, _to):
        call(f'ssh -i {self.key} {self.user}@{self.host} "mkdir {_to}"')

    def delete_file(self, _to):
        call(f'ssh -i {self.key} {self.user}@{self.host} "rm {_to}"')

    def delete_dir(self, _to):
        call(f'ssh -i {self.key} {self.user}@{self.host} "rm -r {_to}"')

    def move(self, _from, _to):
        call(f'ssh -i {self.key} {self.user}@{self.host} "mv {_from} {_to}"')


class EventHandler(FileSystemEventHandler):
    file_cache = set()
    next_clear = time()+300

    def __init__(self, ssh, configs):
        self.ssh = ssh
        self.ignore = configs.get('IGNORE', [])

    def use_cache(self, event):
        seconds = int(time())
        if seconds > self.next_clear:
            self.file_cache = set()
            self.next_clear = seconds + 300
        key = (seconds, event)
        if key in self.file_cache:
            return False
        self.file_cache.add(key)
        return True

    def get_path(self, event, attr='src_path'):
        absolute_path = Path(getattr(event, attr))
        relative_path = getattr(event, attr).replace(str(ssh.local_store)+'/', '')
        dist_path = ssh.remote_dir / relative_path
        return absolute_path, dist_path

    def on_modified(self, event):
        if not isinstance(event, DirModifiedEvent):
            if self.use_cache(event):
                self.ssh.upload(*self.get_path(event))

    def on_created(self, event):
        if self.use_cache(event):
            if isinstance(event, DirCreatedEvent):
                _, dir = self.get_path(event)
                self.ssh.create_dir(dir)
            else:
                _, file = self.get_path(event)
                self.ssh.create_file(file)

    def on_deleted(self, event):
        if self.use_cache(event):
            if isinstance(event, DirDeletedEvent):
                _, dir = self.get_path(event)
                self.ssh.delete_dir(dir)
            else:
                _, file = self.get_path(event)
                self.ssh.delete_file(file)

    def on_moved(self, event):
        if self.use_cache(event):
            _, src = self.get_path(event)
            _, dist = self.get_path(event, 'dest_path')
            self.ssh.move(src, dist)


def load_project_config(dir_path, config_file='.colossos.cfex'):
    config_file = dir_path / config_file
    if not config_file.is_file():
        raise Exception('This folder don\'t have a colossos project!')
    return CFEX(config_file).load()



if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-d", "--dir", required=True, help="directory for sync")
    parser.add_argument("-s", "--sync", default=False, action='store_true', help="sync remote directory")
    args = parser.parse_args(argv[1:])
    
    dir_path = Path(args.dir)
    CONFIGS = load_project_config(dir_path)

    ssh = SSH(CONFIGS)
    if not ssh.check():
        raise Exception('Remote dir don\'t exist!')

    if args.sync:
        ssh.download(CONFIGS['REMOTE_DIR'], True)
    print('Observer started')

    observer = Observer()
    event = EventHandler(ssh, CONFIGS)
    observer.schedule(event, ssh.local_store, recursive=True)
    observer.start()
    observer.join()