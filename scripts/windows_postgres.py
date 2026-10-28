"""Optional workspace-local PostgreSQL, without installing a Windows service."""

import argparse
import hashlib
import os
import subprocess
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / ".tools"
WORK = ROOT / ".work"
BIN = TOOLS / "pgsql/bin"
DATA = WORK / "pgdata"
URL = "https://get.enterprisedb.com/postgresql/postgresql-18.6-5-windows-x64-binaries.zip"
SHA256 = "e2246ba91d22345bc3d017586c09ede52d9df180b1eeb480f050445f1cad84e2"
PORT = "55432"
PASSWORD = "qa_demo_password"  # Public synthetic credential for this loopback lab only.


def run(program, *args, check=True):
    return subprocess.run(
        [str(BIN / f"{program}.exe"), *map(str, args)],
        env={**os.environ, "PGPASSWORD": PASSWORD},
        check=check,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def prepare():
    TOOLS.mkdir(exist_ok=True)
    archive = TOOLS / "postgresql-18.6-5.zip"
    if not archive.exists():
        print(
            "Downloading PostgreSQL 18.6 from the EDB distribution linked by postgresql.org...",
            flush=True,
        )
        temporary = archive.with_suffix(".partial")
        urllib.request.urlretrieve(URL, temporary)
        temporary.replace(archive)
    with archive.open("rb") as source:
        checksum = hashlib.file_digest(source, "sha256").hexdigest()
    if checksum != SHA256:
        raise RuntimeError("PostgreSQL archive checksum mismatch; refusing to extract")
    if not (BIN / "pg_ctl.exe").exists():
        with zipfile.ZipFile(archive) as zipped:
            for name in zipped.namelist():
                if not name.startswith(("pgsql/bin/", "pgsql/lib/", "pgsql/share/")):
                    continue
                target = (TOOLS / name).resolve()
                if not target.is_relative_to(TOOLS.resolve()):
                    raise RuntimeError("Archive member escapes the tools directory")
                zipped.extract(name, TOOLS)
    run("postgres", "--version")
    print("Verified distribution SHA-256. Binaries remain inside ignored .tools/.")


def start():
    if not (BIN / "pg_ctl.exe").exists():
        raise RuntimeError("Run this script with 'prepare' first")
    WORK.mkdir(exist_ok=True)
    if not (DATA / "PG_VERSION").exists():
        password_file = WORK / "bootstrap-password.txt"
        password_file.write_text(PASSWORD, encoding="utf-8")
        try:
            run(
                "initdb",
                "-D",
                DATA,
                "-U",
                "qa_user",
                "-A",
                "scram-sha-256",
                "--pwfile",
                password_file,
                "--encoding=UTF8",
                "--locale=C",
            )
        finally:
            password_file.unlink(missing_ok=True)
    if run("pg_ctl", "-D", DATA, "status", check=False).returncode != 0:
        run(
            "pg_ctl",
            "-D",
            DATA,
            "-l",
            WORK / "postgres.log",
            "-o",
            f"-h 127.0.0.1 -p {PORT}",
            "-w",
            "start",
        )
    result = subprocess.run(
        [
            str(BIN / "psql.exe"),
            "-h",
            "127.0.0.1",
            "-p",
            PORT,
            "-U",
            "qa_user",
            "-d",
            "postgres",
            "-tAc",
            "SELECT 1 FROM pg_database WHERE datname = 'qa_lab'",
        ],
        env={**os.environ, "PGPASSWORD": PASSWORD},
        capture_output=True,
        text=True,
        check=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.stdout.strip() != "1":
        run("createdb", "-h", "127.0.0.1", "-p", PORT, "-U", "qa_user", "qa_lab")
    print("Disposable lab database ready on 127.0.0.1:55432. Stop it after testing.")


def main():
    if os.name != "nt":
        raise SystemExit("This optional helper is Windows-only. Use Compose or native PostgreSQL.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "start", "stop"])
    command = parser.parse_args().command
    if command == "prepare":
        prepare()
    elif command == "start":
        start()
    else:
        run("pg_ctl", "-D", DATA, "-m", "fast", "-w", "stop")


if __name__ == "__main__":
    main()
