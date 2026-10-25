AppSync

Self-hosted APT repository generator. Drop .deb files into debs/, run one script, and get a ready-to-use Packages / Packages.gz index — pure Python standard library, no dependencies, no dpkg-scanpackages required.

How it works

Scans debs/ for .deb archives

Parses the ar archive and the control.tar inside each package using only the Python standard library (tarfile, gzip, hashlib)

Extracts the control metadata (Package, Version, Architecture, Depends, Description, ...)

Appends Filename, Size, and SHA256 for each package

Writes Packages and a max-compression Packages.gz (gzip level 9) next to the repo Release file

Repository layout

.
├── debs/              # drop your .deb files here
├── Packages           # generated index
├── Packages.gz        # generated, gzip level 9
├── Release            # apt release file
└── generate_repo.py   # the generator

Usage

# add a package
cp mypackage_1.0_amd64.deb debs/

# regenerate the index
python3 generate_repo.py

The script validates that every package has Package, Version, and Architecture control fields and aborts with a clear error naming the offending file if one is missing.

Using the repo on a client

Example when hosting the folder as-is on GitHub:

echo "deb [trusted=yes] https://raw.githubusercontent.com/ahmed65-boton/AppSync/main ./" \
  | sudo tee /etc/apt/sources.list.d/appsync.list
sudo apt update
sudo apt install mypackage

[trusted=yes] skips signature checks. For anything public, sign the Release file with GPG and drop the flag.

Notes

Requires Python 3.6+ — standard library only

Re-run the script after adding or removing any .deb; the index is always rebuilt from scratch

Packages are indexed in sorted filename order, so rebuilds are deterministic
