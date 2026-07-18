import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = PROJECT_ROOT / "VERSION"
PYPROJECT_FILE = PROJECT_ROOT / "pyproject.toml"
SOURCE_DIR = PROJECT_ROOT / "src" / "pricing_app"
DIST_DIR = PROJECT_ROOT / "dist"

PROJECT_NAME = "governed-artifact-lifecycle"


def read_version() -> str:
    """Read and validate the version stored in the VERSION file."""

    if not VERSION_FILE.exists():
        raise FileNotFoundError(f"VERSION file not found: {VERSION_FILE}")

    version = VERSION_FILE.read_text(encoding="utf-8").strip()

    if not version:
        raise ValueError("VERSION file cannot be empty.")

    return version


def validate_pyproject_version(expected_version: str) -> None:
    """Confirm that pyproject.toml and VERSION contain the same version."""

    if not PYPROJECT_FILE.exists():
        raise FileNotFoundError(
            f"pyproject.toml file not found: {PYPROJECT_FILE}"
        )

    with PYPROJECT_FILE.open("rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)

    project_version = pyproject["project"]["version"]

    if project_version != expected_version:
        raise ValueError(
            "Version mismatch: "
            f"VERSION contains {expected_version}, "
            f"but pyproject.toml contains {project_version}."
        )


def build_artifact(version: str) -> Path:
    """Create a ZIP artifact containing the application files."""

    if not SOURCE_DIR.exists():
        raise FileNotFoundError(
            f"Application source directory not found: {SOURCE_DIR}"
        )

    DIST_DIR.mkdir(exist_ok=True)

    artifact_name = f"{PROJECT_NAME}-{version}.zip"
    artifact_path = DIST_DIR / artifact_name
    package_root = f"{PROJECT_NAME}-{version}"

    if artifact_path.exists():
        artifact_path.unlink()

    with ZipFile(
        artifact_path,
        mode="w",
        compression=ZIP_DEFLATED,
    ) as zip_file:
        for source_file in sorted(SOURCE_DIR.rglob("*.py")):
            relative_source_path = source_file.relative_to(SOURCE_DIR)

            archive_path = (
                Path(package_root)
                / "pricing_app"
                / relative_source_path
            )

            zip_file.write(
                source_file,
                archive_path.as_posix(),
            )

        zip_file.write(
            VERSION_FILE,
            (Path(package_root) / "VERSION").as_posix(),
        )

        zip_file.write(
            PYPROJECT_FILE,
            (Path(package_root) / "pyproject.toml").as_posix(),
        )

    return artifact_path


def calculate_sha256(file_path: Path) -> str:
    """Calculate the SHA-256 checksum of a file."""

    sha256 = hashlib.sha256()

    with file_path.open("rb") as input_file:
        while chunk := input_file.read(8192):
            sha256.update(chunk)

    return sha256.hexdigest()


def write_checksum_file(
    artifact_path: Path,
    checksum: str,
) -> Path:
    """Write the artifact checksum to a companion file."""

    checksum_path = (
        artifact_path.parent
        / f"{artifact_path.name}.sha256"
    )

    checksum_path.write_text(
        f"{checksum}  {artifact_path.name}\n",
        encoding="utf-8",
    )

    return checksum_path


def run_git_command(*arguments: str) -> str:
    """Run a Git command and return its text output."""

    result = subprocess.run(
        ["git", *arguments],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    return result.stdout.strip()


def collect_git_metadata() -> dict[str, str | bool]:
    """Collect traceability information from the Git repository."""

    commit = run_git_command("rev-parse", "HEAD")
    branch = run_git_command("branch", "--show-current")
    status = run_git_command("status", "--porcelain")

    return {
        "commit": commit,
        "branch": branch,
        "working_tree_clean": status == "",
    }


def write_build_metadata(
    artifact_path: Path,
    version: str,
    checksum: str,
) -> Path:
    """Create a JSON document describing how the artifact was built."""

    git_metadata = collect_git_metadata()

    metadata = {
        "schema_version": "1.0",
        "project": {
            "name": PROJECT_NAME,
            "version": version,
        },
        "artifact": {
            "name": artifact_path.name,
            "size_bytes": artifact_path.stat().st_size,
            "sha256": checksum,
        },
        "source": git_metadata,
        "build": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "build_number": os.getenv("BUILD_NUMBER", "local"),
            "builder": os.getenv("BUILD_ACTOR", "local-developer"),
            "python_version": platform.python_version(),
            "operating_system": platform.system(),
        },
    }

    metadata_path = DIST_DIR / "build-metadata.json"

    metadata_path.write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )

    return metadata_path


def main() -> None:
    """Execute the complete artifact build process."""

    version = read_version()
    validate_pyproject_version(version)

    artifact_path = build_artifact(version)
    checksum = calculate_sha256(artifact_path)

    checksum_path = write_checksum_file(
        artifact_path,
        checksum,
    )

    metadata_path = write_build_metadata(
        artifact_path,
        version,
        checksum,
    )

    print(f"Artifact successfully built: {artifact_path}")
    print(f"Checksum file created: {checksum_path}")
    print(f"Build metadata created: {metadata_path}")
    print(f"Artifact version: {version}")
    print(f"Artifact SHA-256: {checksum}")


if __name__ == "__main__":
    main()