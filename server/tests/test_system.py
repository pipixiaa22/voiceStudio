import os
import tempfile
from pathlib import Path


def test_ls_default_returns_200_or_400(client):
    """Default path may not exist on CI, but the endpoint should respond."""
    resp = client.get('/api/system/ls')
    assert resp.status_code in (200, 400)


def test_ls_specific_directory(client):
    """Listing a known directory should return entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / 'subA').mkdir()
        (Path(tmpdir) / 'subB').mkdir()
        (Path(tmpdir) / '.hidden').mkdir()
        resp = client.get(f'/api/system/ls?path={tmpdir}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['current'] == str(Path(tmpdir).resolve())
        assert data['parent'] is not None
        names = [e['name'] for e in data['entries']]
        assert 'subA' in names
        assert 'subB' in names
        assert '.hidden' not in names


def test_ls_nonexistent_path(client):
    resp = client.get('/api/system/ls?path=/nonexistent/path/xyz')
    assert resp.status_code == 400
    assert '不存在' in resp.get_json()['error']


def test_ls_file_not_directory(client):
    with tempfile.NamedTemporaryFile(suffix='.txt') as f:
        resp = client.get(f'/api/system/ls?path={f.name}')
        assert resp.status_code == 400
        assert '不是目录' in resp.get_json()['error']
