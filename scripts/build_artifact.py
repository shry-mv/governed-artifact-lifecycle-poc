import hashlib
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


def write_checksum_file(artifact_path: Path) -> Path:
    """Write the artifact SHA-256 checksum to a companion file."""

    checksum = calculate_sha256(artifact_path)

    checksum_path = (
        artifact_path.parent
        / f"{artifact_path.name}.sha256"
    )

    checksum_path.write_text(
        f"{checksum}  {artifact_path.name}\n",
        encoding="utf-8",
    )

    return checksum_path


def main() -> None:
    """Execute the complete artifact build process."""

    version = read_version()
    validate_pyproject_version(version)

    artifact_path = build_artifact(version)
    checksum_path = write_checksum_file(artifact_path)

    print(f"Artifact successfully built: {artifact_path}")
    print(f"Checksum file created: {checksum_path}")
    print(f"Artifact version: {version}")


if __name__ == "__main__":
    main()