import struct
from collections.abc import Iterator
from pathlib import Path


def read_dbf(path: Path) -> Iterator[dict[str, str]]:
    """Read a .dbf table record by record, each record as a column -> value dict.

    The encoding comes from the .cpg file next to it; padding spaces are stripped.
    """
    with path.open("rb") as fh:
        header = fh.read(32)
        n_records, header_len, record_len = struct.unpack("<I H H", header[4:12])
        encoding = path.with_suffix(".cpg").read_text(encoding="ascii").strip()

        fields: list[tuple[str, int]] = []
        while (desc := fh.read(32))[0] != 0x0D:
            fields.append((desc[:11].split(b"\x00")[0].decode("ascii"), desc[16]))

        fh.seek(header_len)
        for _ in range(n_records):
            record = fh.read(record_len)
            if record[0:1] == b"*":
                continue
            row, pos = {}, 1
            for name, length in fields:
                row[name] = record[pos : pos + length].decode(encoding).strip()
                pos += length
            yield row
