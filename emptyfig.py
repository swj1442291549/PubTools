import glob
import argparse

from shutil import copyfile
from pathlib import Path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "filename", type=str, help="filename of tex file (ms.tex)")
    args = parser.parse_args()
    filename = args.filename

    source = "/Users/weijia/Github/PubTools/empty.pdf"

    for pdf_filename in glob.glob("*.pdf"):
        if Path(pdf_filename).stem != Path(filename).stem:
            copyfile(source, pdf_filename)
            

