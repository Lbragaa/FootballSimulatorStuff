"""Explicit opt-in logon task; no issue can enable or alter startup."""

import os
import csv
import re
from pathlib import Path
import subprocess
import sys
import tempfile
from xml.sax.saxutils import escape


def enable(config_path, repository_id):
    if os.name != "nt":
        raise ValueError("Windows startup only")
    config_path = Path(config_path).resolve()
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.is_file():
        raise ValueError("pythonw unavailable")
    name = f"BragaEraBridge-{repository_id}"
    whoami = Path(os.environ["SystemRoot"]) / "System32/whoami.exe"
    actor = subprocess.run(
        [str(whoami), "/user", "/fo", "csv", "/nh"],
        capture_output=True,
        text=True,
        check=True,
    )
    sid = next(csv.reader(actor.stdout.splitlines()))[1]
    if not re.fullmatch(r"S-[0-9-]+", sid):
        raise ValueError("Windows account SID unavailable")
    prior = subprocess.run(
        ["schtasks", "/Query", "/TN", name, "/XML"], capture_output=True
    )
    if prior.returncode == 0:
        raise ValueError("Startup task exists; inspect or disable it explicitly")
    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
<RegistrationInfo><Description>Braga Era local GitHub worker; explicitly enabled</Description></RegistrationInfo>
<Triggers><LogonTrigger><Enabled>true</Enabled><UserId>{escape(sid)}</UserId></LogonTrigger></Triggers>
<Principals><Principal id="Author"><UserId>{escape(sid)}</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
<Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><StartWhenAvailable>true</StartWhenAvailable><ExecutionTimeLimit>PT0S</ExecutionTimeLimit><RestartOnFailure><Interval>PT1M</Interval><Count>999</Count></RestartOnFailure></Settings>
<Actions Context="Author"><Exec><Command>{escape(str(pythonw))}</Command><Arguments>{escape('-m braga_era.bridge --config "'+str(config_path)+'" run')}</Arguments><WorkingDirectory>{escape(str(config_path.parent))}</WorkingDirectory></Exec></Actions></Task>"""
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "startup.xml"
        path.write_text(xml, encoding="utf-16")
        done = subprocess.run(
            ["schtasks", "/Create", "/TN", name, "/XML", str(path)], capture_output=True
        )
    if done.returncode:
        raise RuntimeError(
            "Startup registration failed; no password or elevation is requested"
        )


def disable(repository_id):
    if os.name != "nt":
        raise ValueError("Windows startup only")
    done = subprocess.run(
        ["schtasks", "/Delete", "/TN", f"BragaEraBridge-{repository_id}", "/F"],
        capture_output=True,
    )
    if done.returncode:
        raise RuntimeError("Startup removal failed")
