"""Chỉ chạy lại case unscored vì lỗi hạ tầng/judge; giữ nguyên case đã chấm.

python run_with_env.py --baseline analysis/retry_unscored.py eval_before.json
python run_with_env.py analysis/retry_unscored.py eval_after.json
"""
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evals'))
from run_evals import run_case
from grading import summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--attempts', type=int, default=2)
    options = parser.parse_args()
    path = options.report.resolve()
    report = json.loads(path.read_text(encoding='utf-8'))
    config = report['config']
    args = SimpleNamespace(**config, bonus=config['dataset'] == 'bonus')
    cases_file = ROOT / ('bonus' if args.bonus else 'evals') / 'cases.json'
    cases = {c['id']: c for c in json.loads(cases_file.read_text(encoding='utf-8'))}
    original = ROOT / 'analysis' / (path.stem + '_initial.json')
    if not original.exists():
        original.write_text(path.read_text(encoding='utf-8'), encoding='utf-8')
    for attempt in range(1, options.attempts + 1):
        pending = [i for i, item in enumerate(report['cases']) if item['grade']['score'] is None]
        if not pending:
            break
        for index in pending:
            previous = report['cases'][index]
            print(f"Retry {attempt}: {previous['id']} ({previous['grade']['reason']})", flush=True)
            item = run_case(cases[previous['id']], args)
            report['cases'][index] = item
            report.setdefault('infrastructure_retries', []).append({
                'id': item['id'], 'attempt': attempt,
                'previous_reason': previous['grade']['reason'],
                'score': item['grade']['score'], 'status': item['grade']['status'],
            })
            report['summary'] = summarize(report['cases'])
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(f"{item['id']}: {item['grade']['score']} ({item['grade']['status']})", flush=True)
    print(json.dumps(report['summary'], ensure_ascii=False), flush=True)
    return 0 if report['summary']['unscored_cases'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
