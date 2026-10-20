"""镜像名称来自实时平台查询，过滤和分页不会触发写入。"""
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from scripts.cli import main
from scripts.mirror_manager import MirrorManager


class Client:
    def __init__(self):
        self.calls = []

    def get(self, path, *, params=None):
        self.calls.append((path, params))
        return {'items': [{'id': 8, 'name': 'remote-image', 'version': '2.0.0'}],
                'total': 51, 'total_page': 2}


class ImageLookupTests(unittest.TestCase):
    def test_filters_and_pagination_reach_platform(self):
        client = Client()
        result = MirrorManager(client).list(page=2, per_page=50, name='remote', version='2.0.0')
        self.assertEqual(client.calls, [('/dev/images', {'page': 2, 'per_page': 50,
                          'name': 'remote', 'version': '2.0.0'})])
        self.assertEqual(result['items'][0]['name'], 'remote-image')

    def test_detail_uses_exact_platform_id(self):
        client = Client()
        MirrorManager(client).get(8)
        self.assertEqual(client.calls, [('/dev/images/8', None)])

    def test_cli_dry_run_is_offline_with_filters(self):
        with patch('scripts.asterfire_client.request_json', side_effect=AssertionError('unexpected network')):
            with redirect_stdout(io.StringIO()) as output:
                with patch('sys.argv', ['cli', '--dry-run', 'image', 'list', '--name', 'remote', '--page', '2', '--per-page', '50']):
                    main()
        result = json.loads(output.getvalue())
        self.assertEqual(result['operation'], 'GET /dev/images')
        self.assertEqual(result['query']['page'], 2)

    def test_cli_detail_dry_run_is_offline(self):
        with patch('scripts.asterfire_client.request_json', side_effect=AssertionError('unexpected network')):
            with redirect_stdout(io.StringIO()) as output:
                with patch('sys.argv', ['cli', '--dry-run', 'image', 'get', '--image-id', '8']):
                    main()
        self.assertEqual(json.loads(output.getvalue())['operation'], 'GET /dev/images/8')


if __name__ == '__main__':
    unittest.main()
