"""Nạp .env dạng KEY=VALUE rồi chạy CLI gốc, không thực thi lệnh trong .env.

python run_with_env.py evals/run_evals.py --output eval_after.json
python run_with_env.py --baseline evals/run_evals.py --output eval_before.json
python run_with_env.py run.py "GitHub Actions có sự cố không?"
"""
import importlib.util
import os
from pathlib import Path
import re
import runpy
import sys

ROOT = Path(__file__).resolve().parent


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    args = sys.argv[1:]
    baseline = bool(args and args[0] == '--baseline')
    if baseline:
        args.pop(0)
    if not args or args[0] not in ('run.py', 'evals/run_evals.py', 'analysis/retry_unscored.py'):
        print('Usage: python run_with_env.py [--baseline] '
              '{run.py|evals/run_evals.py} [arguments]', file=sys.stderr)
        return 2
    env_path = ROOT / '.env'
    if env_path.exists():
        for number, line in enumerate(env_path.read_text(encoding='utf-8-sig').splitlines(), 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('export '):
                line = line[7:].strip()
            key, separator, value = line.partition('=')
            key, value = key.strip(), value.strip()
            if not separator or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key):
                raise ValueError(f'.env dòng {number}: cần KEY=VALUE.')
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            if value:
                os.environ[key] = value
    if baseline:
        spec = importlib.util.spec_from_file_location('agent', ROOT / 'analysis' / 'agent_before.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules['agent'] = module
    script = ROOT / args[0]
    sys.path.insert(0, str(script.parent))
    sys.argv = [str(script), *args[1:]]
    runpy.run_path(str(script), run_name='__main__')
    return 0


if __name__ == '__main__':
    sys.exit(main())
