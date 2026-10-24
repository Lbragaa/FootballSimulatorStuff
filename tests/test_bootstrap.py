import hashlib
import zipfile

import pytest

from tools import bootstrap_handoff as bootstrap


def test_changed_zip_rejected_before_extraction(tmp_path):
    archive = tmp_path / "changed.zip"
    archive.write_bytes(b"not the original handoff")
    destination = tmp_path / "output"
    with pytest.raises(ValueError, match="checksum"):
        bootstrap.extract(archive, destination)
    assert not destination.exists()


@pytest.mark.parametrize("name", ["../escape.txt", "/escape.txt", "C:/escape.txt", "folder\\escape.txt"])
def test_unsafe_archive_paths_rejected(tmp_path, monkeypatch, name):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        # ZipInfo's constructor normalizes backslashes on Windows. Assign the
        # raw member name afterwards to actually exercise a malformed ZIP.
        member = zipfile.ZipInfo()
        member.filename = name
        bundle.writestr(member, "unsafe")
    monkeypatch.setattr(bootstrap, "ARCHIVE_SHA256", bootstrap.sha256(archive))
    destination = tmp_path / "output"
    with pytest.raises(ValueError, match="Unsafe"):
        bootstrap.extract(archive, destination)
    assert not destination.exists()


def test_reproducible_and_refuses_changed_files(tmp_path, monkeypatch):
    archive = tmp_path / "small.zip"
    content = b"preserved bytes\n"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("canonical/example.txt", content)
        bundle.writestr("MANIFEST_SHA256.txt", hashlib.sha256(content).hexdigest() + "  canonical/example.txt\n")
    monkeypatch.setattr(bootstrap, "ARCHIVE_SHA256", bootstrap.sha256(archive))
    destination = tmp_path / "output"
    bootstrap.extract(archive, destination)
    bootstrap.extract(archive, destination)
    target = destination / "canonical/example.txt"
    assert target.read_bytes() == content
    target.write_bytes(b"changed independently")
    with pytest.raises(ValueError, match="Refusing to overwrite"):
        bootstrap.extract(archive, destination)
    assert target.read_bytes() == b"changed independently"
