import zipfile
from pathlib import Path


def unzip_to(src_zip: Path, dest_dir: Path) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(src_zip, "r") as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            # avoid zip slip
            target = dest_dir / Path(info.filename).name  # flatten simple case
            with z.open(info) as src, target.open("wb") as out:
                out.write(src.read())
            extracted.append(target)
    return extracted


def zip_files(files: list[Path], out_zip: Path) -> Path:
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, arcname=f.name)
    return out_zip
