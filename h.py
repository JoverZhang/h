#!/bin/python3
import os
import shutil
import sys
import tempfile
from argparse import Namespace, ArgumentParser
from typing import Dict, Any, Optional, List


def replace_env(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    for k in list(os.environ.keys()):
        s = s.replace(f'${k}', os.getenv(k))
    return os.path.expanduser(s)


def parse_args() -> Namespace:
    parser: ArgumentParser = ArgumentParser()
    parser.add_argument('-f', '--file',
                        dest='config_file',
                        type=str, default='~/.config/h_command/config.ini',
                        help='config file')
    parser.add_argument('-i', '--interactive',
                        dest='interactive', action='store_true',
                        help='interactive mode')
    args: Namespace = parser.parse_args()
    args.config_file = replace_env(args.config_file)
    return args


class HException(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class H:
    def __init__(self, args: Namespace):
        self.args = args
        self.config = self.load_ini(self.args.config_file)
        includes: str = self.config['global'].get('includes')
        if includes:
            for include in includes.split(','):
                filename = replace_env(include.strip())
                self.config.update(self.load_ini(filename))

    def run(self) -> bool:
        cmd = 'fzf --nth=1 --reverse +s --inline-info --height 35% --no-mouse'

        rows: List[str] = []
        width = 0
        for k in self.config.keys():
            if len(k) > width:
                width = len(k)
        for k in self.config.keys():
            v = self.config[k]
            if k == 'global':
                continue
            k = k + ' ' * (width - len(k) + 2)
            rows.append(f'{k}:{v["command"].strip()}\n')

        tmpdir = tempfile.mkdtemp('h')
        tmpname = os.path.join(tmpdir, 'command.txt')
        tmpoutput = os.path.join(tmpdir, 'output.txt')
        if os.path.exists(tmpoutput):
            os.remove(tmpoutput)
        with open(tmpname, 'w', encoding='utf-8') as f:
            for i in rows:
                f.write(i)
        if sys.platform[:3] != 'win':
            cmd += f' <"{tmpname}" > "{tmpoutput}"'
        else:
            raise HException('unsupport windows platform')
        code = os.system(cmd)
        if code != 0:
            return False
        with open(tmpoutput, mode='r', encoding='utf-8') as f:
            command = f.read().strip('\r\n\t ')
            ops = command.find(':')
            if ops < 0:
                return False
            command = command[ops + 1:].rstrip('\r\n\t ')
            if not command:
                return False
            print(Colors.OKBLUE + command + Colors.ENDC)
            actual_command = self._handle_variable(command)
            if actual_command != command:
                print(Colors.OKBLUE + actual_command + Colors.ENDC)
            os.system(actual_command)
        # remove tmpdir
        if tmpdir:
            shutil.rmtree(tmpdir)
        return True

    @staticmethod
    def _handle_variable(command) -> str:
        mark_open = '$(?'
        mark_close = ')'
        while True:
            p1 = command.find(mark_open)
            if p1 < 0:
                break
            p2 = command.find(mark_close, p1)
            name = command[p1 + len(mark_open): p2]
            data = input(f'Input argument ({name}): ')
            if data is None:
                data = ''
            mark = mark_open + name + mark_close
            command = command.replace(mark, data)
            if p2 < 0:
                break
        return command

    @staticmethod
    def load_ini(filename: str) -> Dict[str, Any]:
        if not os.path.exists(filename):
            raise HException(f'config file "{filename}" not found')

        # read config file
        content = None
        for encoding in ['utf-8', 'latin1', 'gbk']:
            try:
                with open(filename, mode='r', encoding=encoding) as f:
                    content = f.read()
                    break
            except Exception:
                pass
        if not content:
            raise HException(f'unable to read file "{filename}"')

        # parse content
        config = {}
        sect = 'global'
        for line in content.split('\n'):
            line = line.strip('\r\n\t ')
            if not line:
                continue
            elif line[:1] in ('#', ';'):
                continue
            elif line.startswith('['):
                if line.endswith(']'):
                    sect = line[1:-1].strip('\r\n\t ')
                    if sect not in config:
                        config[sect] = {}
            else:
                pos = line.find('=')
                if pos >= 0:
                    key = line[:pos].rstrip('\r\n\t ')
                    val = line[pos + 1:].rstrip('\r\n\t ')
                    if sect not in config:
                        config[sect] = {}
                    config[sect][key] = val
        return config


if __name__ == '__main__':
    try:
        H(parse_args()).run()
    except Exception as e:
        print(e)
