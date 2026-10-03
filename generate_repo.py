from pathlib import Path
import tarfile
import gzip
import hashlib
import io
import struct

ROOT = Path(__file__).resolve().parent
DEBS = ROOT / "debs"
PACKAGES = ROOT / "Packages"
PACKAGES_GZ = ROOT / "Packages.gz"


def read_ar_members(data):
    if data[:8] != b"!<arch>\n":
        raise ValueError("Not a valid .deb (ar) archive.")

    pos = 8
    while pos < len(data):
        header = data[pos:pos + 60]
        if len(header) < 60:
            raise ValueError("Invalid ar member header.")

        name = header[0:16].decode("utf-8", "replace").strip()
        size = int(header[48:58].decode("ascii").strip())
        start = pos + 60
        end = start + size

        yield name.rstrip("/")
        yield data[start:end]

        pos = end + (size & 1)


def ar_members(data):
    if data[:8] != b"!<arch>\n":
        raise ValueError("Not a valid .deb (ar) archive.")

    pos = 8
    while pos < len(data):
        header = data[pos:pos + 60]
        if len(header) < 60:
            raise ValueError("Invalid ar member header.")

        name = header[0:16].decode("utf-8", "replace").strip().rstrip("/")
        size = int(header[48:58].decode("ascii").strip())
        start = pos + 60
        end = start + size

        yield name, data[start:end]

        pos = end + (size & 1)


def extract_control(deb_data):
    for name, payload in ar_members(deb_data):
        if name.startswith("control.tar"):
            with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as tar:
                member = next(
                    (m for m in tar.getmembers()
                     if m.name.lstrip("./") == "control"),
                    None
                )
                if member is None:
                    raise ValueError("control file not found in .deb")

                extracted = tar.extractfile(member)
                if extracted is None:
                    raise ValueError("Could not read control file")

                return extracted.read().decode("utf-8", "replace")

    raise ValueError("control archive not found in .deb")


def parse_control(control):
    fields = {}
    current = None

    for line in control.splitlines():
        if not line:
            continue

        if line[0].isspace() and current:
            fields[current] += "\n" + line
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        current = key.strip()
        fields[current] = value.strip()

    return fields


def format_entry(fields, filename, size, sha256):
    preferred = [
        "Package",
        "Version",
        "Architecture",
        "Priority",
        "Section",
        "Maintainer",
        "Installed-Size",
        "Depends",
        "Recommends",
        "Suggests",
        "Conflicts",
        "Replaces",
        "Provides",
        "Essential",
        "Description",
    ]

    lines = []

    for key in preferred:
        if key in fields:
            value = fields[key]

            if "\n" in value:
                parts = value.splitlines()
                lines.append(f"{key}: {parts[0]}")
                lines.extend(parts[1:])
            else:
                lines.append(f"{key}: {value}")

    for key, value in fields.items():
        if key not in preferred:
            if "\n" in value:
                parts = value.splitlines()
                lines.append(f"{key}: {parts[0]}")
                lines.extend(parts[1:])
            else:
                lines.append(f"{key}: {value}")

    lines.append(f"Filename: {filename}")
    lines.append(f"Size: {size}")
    lines.append(f"SHA256: {sha256}")

    return "\n".join(lines)


def main():
    DEBS.mkdir(exist_ok=True)

    packages = []
    deb_files = sorted(DEBS.glob("*.deb"))

    if not deb_files:
        print("No .deb files found in:", DEBS)
        return

    for deb in deb_files:
        print("Reading:", deb.name)

        data = deb.read_bytes()
        fields = parse_control(extract_control(data))

        if "Package" not in fields:
            raise ValueError(f"{deb.name}: missing Package field")
        if "Version" not in fields:
            raise ValueError(f"{deb.name}: missing Version field")
        if "Architecture" not in fields:
            raise ValueError(f"{deb.name}: missing Architecture field")

        sha256 = hashlib.sha256(data).hexdigest()
        filename = f"debs/{deb.name}"

        packages.append(
            format_entry(
                fields,
                filename,
                len(data),
                sha256
            )
        )

    output = "\n\n".join(packages) + "\n"

    PACKAGES.write_text(output, encoding="utf-8")

    with gzip.open(PACKAGES_GZ, "wb", compresslevel=9) as gz:
        gz.write(output.encode("utf-8"))

    print()
    print(f"Generated {PACKAGES.name}")
    print(f"Generated {PACKAGES_GZ.name}")
    print(f"Indexed {len(deb_files)} package(s).")


if __name__ == "__main__":
    main()