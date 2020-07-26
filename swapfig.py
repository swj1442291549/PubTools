import glob
import hashlib
import argparse

from shutil import copyfile, rmtree
from pathlib import Path


def cal_md5(filename):
    hasher = hashlib.md5()
    with open(filename, "rb") as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Swap or Reverse")
    parser.add_argument("-r", "--reverse", action="store_true")
    args = parser.parse_args()
    is_reverse = args.reverse

    tex_stems = list()
    for filename in glob.glob("*.tex"):
        tex_stems.append(Path(filename).stem)

    if not is_reverse:
        p = Path(".figure")
        if not p.is_dir():
            p.mkdir(parents=True)

        source = "/Users/weijia/Github/PubTools/empty.pdf"
        md5_empty = cal_md5(source)

        for pdf_filename in glob.glob("*.pdf"):
            if Path(pdf_filename).stem in tex_stems:
                continue
            target = Path(".figure", pdf_filename)
            if not target.is_file() or cal_md5(pdf_filename) != md5_empty:
                copyfile(pdf_filename, target)
                copyfile(source, pdf_filename)
    else:
        for pdf_filename in glob.glob(".figure/*.pdf"):
            copyfile(pdf_filename, Path(Path.cwd(), Path(pdf_filename).name))
        rmtree(".figure")
