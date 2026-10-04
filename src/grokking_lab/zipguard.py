from __future__ import annotations

import shutil
import zipfile
from pathlib import Path, PurePosixPath


EOCD = b"PK\x05\x06"
MAX_EOCD_SEARCH = 22 + 65535


def _reject_trailing_data(zip_path: Path) -> None:
    """Reject ZIP/polyglot payloads with bytes after the EOCD record."""
    size = zip_path.stat().st_size
    if size < 22:
        raise ValueError("Upload is not a valid ZIP archive")
    tail_size = min(size, MAX_EOCD_SEARCH)
    with zip_path.open("rb") as stream:
        stream.seek(size - tail_size)
        tail = stream.read(tail_size)
    index = tail.rfind(EOCD)
    if index < 0 or index + 22 > len(tail):
        raise ValueError("Upload is not a valid ZIP archive")
    comment_len = int.from_bytes(tail[index + 20 : index + 22], "little")
    if index + 22 + comment_len != len(tail):
        raise ValueError("ZIP contains unexpected trailing data")


def _entry_type(info: zipfile.ZipInfo) -> int:
    return (info.external_attr >> 16) & 0o170000


def safe_extract_zip(
    zip_path: Path,
    destination: Path,
    *,
    max_entries: int,
    max_total_bytes: int,
    max_file_bytes: int,
) -> None:
    """Validate the whole archive before writing and extract with strict bounds."""
    _reject_trailing_data(zip_path)
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        raise ValueError("Upload is not a valid ZIP archive") from exc

    with zf:
        infos = zf.infolist()
        if len(infos) > max_entries:
            raise ValueError(f"ZIP has too many entries ({len(infos)} > {max_entries})")

        seen: set[str] = set()
        total = 0
        for info in infos:
            raw_name = info.filename
            if not raw_name or "\x00" in raw_name or "\\" in raw_name:
                raise ValueError(f"unsafe ZIP path: {raw_name}")
            parts = PurePosixPath(raw_name).parts
            if raw_name.startswith("/") or ".." in parts or (parts and ":" in parts[0]):
                raise ValueError(f"unsafe ZIP path: {raw_name}")
            if raw_name in seen:
                raise ValueError(f"duplicate ZIP entry: {raw_name}")
            seen.add(raw_name)

            entry_type = _entry_type(info)
            if info.create_system == 3 and entry_type not in (0, 0o100000, 0o040000):
                raise ValueError(f"symlink or special file is not accepted: {raw_name}")
            if info.flag_bits & 0x1:
                raise ValueError(f"encrypted ZIP entry is not accepted: {raw_name}")
            if info.file_size > max_file_bytes:
                raise ValueError(f"ZIP entry exceeds size limit: {raw_name}")
            total += info.file_size
            if total > max_total_bytes:
                raise ValueError("ZIP expands beyond the MVP size limit")

        root = destination.resolve()
        for info in infos:
            target = destination.joinpath(*PurePosixPath(info.filename).parts)
            resolved = target.resolve()
            if resolved != root and root not in resolved.parents:
                raise ValueError(f"unsafe ZIP path: {info.filename}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with zf.open(info) as src, target.open("wb") as dst:
                    copied = 0
                    while True:
                        chunk = src.read(1024 * 1024)
                        if not chunk:
                            break
                        copied += len(chunk)
                        if copied > info.file_size or copied > max_file_bytes:
                            raise ValueError(f"ZIP entry exceeded declared size: {info.filename}")
                        dst.write(chunk)
            except (zipfile.BadZipFile, EOFError, RuntimeError) as exc:
                raise ValueError(f"corrupt ZIP entry: {info.filename}") from exc
