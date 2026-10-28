"""Windows Credential Manager only; secrets never appear in command arguments."""

import os
import ctypes
from ctypes import wintypes


class Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def api():
    if os.name != "nt":
        raise ValueError(
            "Windows Credential Manager required; on Linux use a protected environment credential"
        )
    lib = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    lib.CredWriteW.argtypes = [ctypes.POINTER(Credential), wintypes.DWORD]
    lib.CredWriteW.restype = wintypes.BOOL
    lib.CredReadW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.POINTER(Credential)),
    ]
    lib.CredReadW.restype = wintypes.BOOL
    lib.CredFree.argtypes = [ctypes.c_void_p]
    return lib


def write(target, token):
    if not token.startswith("github_pat_"):
        raise ValueError("Use a fine-grained repository-scoped PAT")
    raw = token.encode("utf-8")
    blob = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
    item = Credential(
        Type=1,
        TargetName=target,
        CredentialBlobSize=len(raw),
        CredentialBlob=blob,
        Persist=2,
        UserName="BragaEraBridge",
    )
    if not api().CredWriteW(ctypes.byref(item), 0):
        raise OSError("Credential storage failed")


def read(target):
    lib = api()
    pointer = ctypes.POINTER(Credential)()
    if not lib.CredReadW(target, 1, 0, ctypes.byref(pointer)):
        raise OSError("Configured credential unavailable")
    try:
        return ctypes.string_at(
            pointer.contents.CredentialBlob, pointer.contents.CredentialBlobSize
        ).decode("utf-8")
    finally:
        lib.CredFree(pointer)
