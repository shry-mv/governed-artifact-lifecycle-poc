import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = PROJECT_ROOT / "dist"
VERSION_FILE = PROJECT_ROOT / "VERSION"
METADATA_FILE = DIST_DIR / "build-metadata.json"

PROJECT_NAME = "governed-artifact-lifecycle"


def calculate_sha256(file_path: Path) -> str:
    """Calculate the SHA-256 checksum of a file."""

    sha256 = hashlib.sha256()

    with file_path.open("rb") as input_file:
        while chunk := input_file.read(8192):
            sha256.update(chunk)

    return sha256.hexdigest()


def load_metadata() -> dict[str, Any]:
    """Load and parse the build metadata document."""

    if not METADATA_FILE.exists():
        raise FileNotFoundError(
            f"Build metadata not found: {METADATA_FILE}"
        )

    with METADATA_FILE.open(encoding="utf-8") as metadata_file:
        return json.load(metadata_file)


def verify_artifact() -> None:
    """Verify the consistency and integrity of the release files."""

    if not VERSION_FILE.exists():
        raise FileNotFoundError(
            f"VERSION file not found: {VERSION_FILE}"
        )

    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    metadata = load_metadata()

    metadata_project_name = metadata["project"]["name"]
    metadata_version = metadata["project"]["version"]

    if metadata_project_name != PROJECT_NAME:
        raise ValueError(
            "Project name mismatch: "
            f"expected {PROJECT_NAME}, "
            f"but metadata contains {metadata_project_name}."
        )

    if metadata_version != version:
        raise ValueError(
            "Version mismatch: "
            f"VERSION contains {version}, "
            f"but metadata contains {metadata_version}."
        )

    expected_artifact_name = f"{PROJECT_NAME}-{version}.zip"
    metadata_artifact_name = metadata["artifact"]["name"]

    if metadata_artifact_name != expected_artifact_name:
        raise ValueError(
            "Artifact name mismatch: "
            f"expected {expected_artifact_name}, "
            f"but metadata contains {metadata_artifact_name}."
        )

    artifact_path = DIST_DIR / metadata_artifact_name
    checksum_path = DIST_DIR / f"{metadata_artifact_name}.sha256"

    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Artifact not found: {artifact_path}"
        )

    if not checksum_path.exists():
        raise FileNotFoundError(
            f"Checksum file not found: {checksum_path}"
        )

    actual_checksum = calculate_sha256(artifact_path)
    metadata_checksum = metadata["artifact"]["sha256"]

    checksum_content = checksum_path.read_text(
        encoding="utf-8"
    ).strip()

    checksum_parts = checksum_content.split(maxsplit=1)

    if len(checksum_parts) != 2:
        raise ValueError(
            "Checksum file has an invalid format."
        )

    checksum_file_hash, checksum_file_name = checksum_parts

    if checksum_file_name != artifact_path.name:
        raise ValueError(
            "Checksum filename mismatch: "
            f"expected {artifact_path.name}, "
            f"but checksum file references {checksum_file_name}."
        )

    if actual_checksum != metadata_checksum:
        raise ValueError(
            "Integrity validation failed: "
            "the artifact checksum does not match the metadata."
        )

    if actual_checksum != checksum_file_hash:
        raise ValueError(
            "Integrity validation failed: "
            "the artifact checksum does not match the checksum file."
        )

    actual_size = artifact_path.stat().st_size
    metadata_size = metadata["artifact"]["size_bytes"]

    if actual_size != metadata_size:
        raise ValueError(
            "Artifact size mismatch: "
            f"actual size is {actual_size} bytes, "
            f"but metadata contains {metadata_size} bytes."
        )

    if not metadata["source"]["working_tree_clean"]:
        raise ValueError(
            "Governance validation failed: "
            "the artifact was built from a dirty working tree."
        )

    print("Artifact verification passed.")
    print(f"Project: {metadata_project_name}")
    print(f"Version: {version}")
    print(f"Artifact: {artifact_path.name}")
    print(f"Size: {actual_size} bytes")
    print(f"SHA-256: {actual_checksum}")
    print(f"Source commit: {metadata['source']['commit']}")
    print(f"Source branch: {metadata['source']['branch']}")


def main() -> None:
    """Execute artifact verification."""

    verify_artifact()


if __name__ == "__main__":
    main()