"""Regenerate the PDF fixtures byte-identically.

Kept beside the fixtures so a reviewer can see what is in them and reproduce
them; the .pdf files themselves are the corpus and are committed.

    python tests/fixtures/corpus/pdf/_generate.py
"""

from pathlib import Path

HERE = Path(__file__).parent


def build(lines: list[str]) -> bytes:
    text = "".join(f"({line}) Tj T*\n" for line in lines)
    stream = f"BT /F1 11 Tf 14 TL 72 720 Td\n{text}ET".encode("latin-1")
    objects = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length " + str(len(stream)).encode() + b">>\nstream\n" + stream + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<</Size {len(objects) + 1}/Root 1 0 R>>\nstartxref\n{xref}\n".encode()
        + b"%%EOF\n"
    )
    return bytes(out)


def main() -> None:
    record = build(
        [
            "NATIONAL AVIATION SAFETY REGISTRY",
            "Occurrence record 2026-0311-CR",
            "",
            "Filed: 4 March 2026. Operator report received 3 March 2026.",
            "Aircraft: commercial passenger, cruise phase, FL340.",
            "Reported by: flight crew, via operator safety channel.",
            "",
            "Radar correlation: none found in the recorded window.",
            "Search window: 2 March 2026, 18:00-20:00 local, Coral Ridge sector.",
            "Status: closed, no further action.",
        ]
    )
    (HERE / "registry_record.pdf").write_bytes(record)

    # Truncated mid-stream: a real header, a real object, and no xref at all.
    (HERE / "truncated.pdf").write_bytes(record[: record.index(b"xref")][:520])


if __name__ == "__main__":
    main()
