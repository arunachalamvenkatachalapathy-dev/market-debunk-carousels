"""Publish each generated slide to an immutable public GitHub commit before Meta sees it."""
import subprocess
from pathlib import Path


def _git(*args):
    return subprocess.run(['git', *args], check=True, text=True, capture_output=True).stdout.strip()


def publish_slides(slide_paths, owner, repo):
    if not slide_paths:
        raise RuntimeError('No slides rendered for Instagram')
    root = Path(__file__).resolve().parents[1]
    relpaths = []
    for path in slide_paths:
        p = Path(path).resolve()
        if not p.is_file() or p.stat().st_size == 0 or not p.is_relative_to(root / 'state/carousel_slides'):
            raise RuntimeError(f'Invalid slide path: {p}')
        relpaths.append(str(p.relative_to(root)))
    _git('config', 'user.name', 'github-actions[bot]')
    _git('config', 'user.email', 'github-actions[bot]@users.noreply.github.com')
    _git('add', '-f', '--', *relpaths)
    _git('commit', '-m', 'chore: host carousel slides for Meta [skip ci]')
    # Fail closed on conflict/push rejection. Do not link unpublished images.
    _git('push', 'origin', 'HEAD:master')
    sha = _git('rev-parse', 'HEAD')
    return [f'https://raw.githubusercontent.com/{owner}/{repo}/{sha}/{p}' for p in relpaths]
