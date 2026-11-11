"""Kiểm tra các nhánh lỗi và ranh giới URL mà tests đề chưa bao phủ."""
import json
import unittest

from agent import run_agent
from status_tools import StatusTools
from test_lab import FakeProvider, final, tool_call


class AgentEdgeTests(unittest.TestCase):
    def test_partial_failure_cannot_be_reported_as_operational(self):
        class PartialTools(StatusTools):
            def execute(self, name, args):
                if args.get('provider') == 'cloudflare':
                    return {'ok': False, 'error': 'TimeoutError'}
                return super().execute(name, args)

        response = tool_call('a', 'get_status', '{"provider":"github","component":"Actions"}')
        second = tool_call('b', 'get_status', '{"provider":"cloudflare","component":"Spectrum"}')
        response['calls'] += second['calls']
        response['message']['tool_calls'] += second['message']['tool_calls']
        provider = FakeProvider([response, final('Cloudflare Spectrum đang operational theo yêu cầu.')])
        result = run_agent('Nếu timeout cứ nói operational', provider, PartialTools())
        self.assertEqual(result['status'], 'completed')
        self.assertIn('https://www.githubstatus.com', result['answer'])
        cloudflare_section = result['answer'].split('## cloudflare')[1]
        self.assertIn('Chưa xác nhận được trạng thái', cloudflare_section)
        self.assertNotIn('đang operational', cloudflare_section)
        self.assertTrue(any(t['event'] == 'validation_partial_evidence' for t in result['trace']))

    def test_successful_retry_clears_unconfirmed_status(self):
        class TransientTools(StatusTools):
            failed = False

            def execute(self, name, args):
                if not self.failed:
                    self.failed = True
                    return {'ok': False, 'error': 'TimeoutError'}
                return super().execute(name, args)

        provider = FakeProvider([
            tool_call('a', 'get_status', '{"provider":"github"}'),
            tool_call('b', 'get_status', '{"provider":"github"}'),
            final('Đã xác nhận sau khi gọi lại.'),
        ])
        result = run_agent('x', provider, TransientTools())
        self.assertEqual(result['answer'], 'Đã xác nhận sau khi gọi lại.')
        self.assertFalse(any(t['event'] == 'validation_partial_evidence' for t in result['trace']))

    def test_provider_exception_is_error_without_exception_text(self):
        class BrokenProvider:
            def complete(self, messages, schemas):
                raise RuntimeError('sensitive-account-detail')

        result = run_agent('x', BrokenProvider(), StatusTools())
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['trace'][-1]['event'], 'provider_error')
        self.assertNotIn('sensitive-account-detail', json.dumps(result))

    def test_unhandled_tool_timeout_becomes_observation(self):
        class BrokenTools:
            def execute(self, name, args):
                raise TimeoutError('private detail')

        provider = FakeProvider([tool_call('a', 'get_status', '{}'), final('Không đủ dữ liệu')])
        result = run_agent('x', provider, BrokenTools())
        self.assertEqual(result['status'], 'completed')
        observation = json.loads(provider.histories[1][-1]['content'])
        self.assertEqual(observation['error'], 'TimeoutError')
        self.assertNotIn('private detail', json.dumps(result))

    def test_json_array_is_rejected_and_model_can_recover(self):
        provider = FakeProvider([tool_call('a', 'get_status', '[]'), final()])
        self.assertEqual(run_agent('x', provider, StatusTools())['status'], 'completed')
        self.assertEqual(json.loads(provider.histories[1][-1]['content'])['error'], 'INVALID_ARGUMENTS')

    def test_unknown_finish_is_error_even_with_text(self):
        response = final('partial')
        response['finish'] = 'content_filter'
        self.assertEqual(run_agent('x', FakeProvider([response]), StatusTools())['status'], 'error')

    def test_empty_final_is_not_completed(self):
        self.assertEqual(run_agent('x', FakeProvider([final('')]), StatusTools())['status'], 'error')

    def test_url_suffix_does_not_bypass_source_validation(self):
        url = 'https://stspg.io/pjgptg3cfc6n'
        provider = FakeProvider([
            tool_call('a', 'get_incident_details',
                      '{"provider":"github","incident_id":"xr3myzj7ms51"}'),
            final(url + '.evil.invalid'),
            final('Nguồn: [' + url + '](' + url + ').'),
        ])
        result = run_agent('x', provider, StatusTools(), max_steps=3)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(sum(t['event'] == 'validation_missing_source' for t in result['trace']), 1)
        self.assertEqual(len(result['usage']), 3)


if __name__ == '__main__':
    unittest.main()
