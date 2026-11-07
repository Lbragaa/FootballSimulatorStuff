"""Release only this CI job's completed pytest copies; preserve reports/sources."""
import os
from pathlib import Path
import shutil


def main():
    if os.environ.get('GITHUB_ACTIONS')!='true':raise ValueError('CI-only cleanup')
    root=Path(__file__).resolve().parents[1]
    expected=root/'output'/'ci-test-copies'
    target=expected.resolve()
    if target!=expected or target.parent.parent!=root or target.is_symlink():raise ValueError('Unsafe CI cleanup target')
    if target.exists():shutil.rmtree(target)


if __name__=='__main__':main()
