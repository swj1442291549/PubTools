import argparse
import glob
import logging
import os
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

import adsapi

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sortref")


def read_bib(filename: Path) -> pd.DataFrame:
    r"""Read bib from the tex file.

    separate the bibitem into cite, key, bib

    "\bibitem[cite]{key} bib"

    Args:
        filename (Path): file name

    Returns:
        df (pd.DataFrame): bib data
    """
    bib_items = list()
    with open(filename) as f:
        bib_tag = False
        bib_lines = list()
        for line in f:
            if "\\end{thebibliography}" in line:
                bib_tag = False
                item = "".join(bib_lines)
                if item != "":
                    bib_items.append(item)
            if bib_tag:
                if line.strip() != "":
                    if "\\bibitem[" in line:
                        if len(bib_lines) > 0:
                            bib_items.append(" ".join(bib_lines))
                        bib_lines = [line.strip()]
                    else:
                        bib_lines.append(line.strip())
            if "\\begin{thebibliography}" in line:
                bib_tag = True
    info_list = list()
    pd.options.mode.chained_assignment = None  # type: ignore
    if len(bib_items) > 0:
        for bib_item in bib_items:
            info_list.append(extract_info(bib_item))
        df = pd.DataFrame(info_list)
    else:
        df = pd.DataFrame(
            columns=[
                "au1_f",
                "au1_l",
                "au2_f",
                "au2_l",
                "au3_f",
                "au3_l",
                "au1_f_low",
                "au1_l_low",
                "au2_f_low",
                "au2_l_low",
                "au3_f_low",
                "au3_l_low",
                "bib",
                "cite",
                "key",
                "num",
                "year",
            ]
        )
    return df


def extract_info(bib_item: str) -> dict:
    """Extract info from bib_item.

    Args:
        bib_item (str): bib item

    Returns:
        info (dict): info dictionary
    """
    info = dict()
    info["cite"] = bib_item.split("\\bibitem[")[1].split("]")[0]
    info["key"] = (
        bib_item.split("\\bibitem[")[1].split("]")[1].split("{")[1].split("}")[0]
    )
    bib = (
        bib_item.split("\\bibitem[")[1]
        .split("]")[1][bib_item.split("\\bibitem[")[1].split("]")[1].find("}") + 1 :]
        .strip()
    )
    if bib[-1] == ".":
        info["bib"] = bib[:-1]
    else:
        info["bib"] = bib
    info["year"] = info["key"][:4]
    assert info["year"].isdigit(), f"year cannot be extracted from {info['key']}"
    bib = info["bib"][: info["bib"].find(info["year"])]
    if "et al." not in info["cite"] and "\\&" not in info["cite"]:
        f = info["cite"].split("(")[0].strip()
        info["au1_f"] = f
        info["au1_l"] = bib[bib.find(f) + len(f) + 1 :].split(".")[0].strip()
        info["au2_f"] = ""
        info["au2_l"] = ""
        info["au3_f"] = ""
        info["au3_l"] = ""
        info["num"] = 1
    elif "\\&" in info["cite"] and "et al." not in info["cite"]:
        f1 = info["cite"].split("\\&")[0].strip()
        if f1[-1] == ",":
            f1 = f1[:-1]
        info["au1_f"] = f1
        info["au1_l"] = bib[bib.find(f1) + len(f1) + 1 :].split(".")[0].strip()
        f2 = info["cite"].split("\\&")[1].split("(")[0].strip()
        l2 = bib[bib.find(f1) + len(f1) + 1 :]
        info["au2_f"] = f2
        info["au2_l"] = l2[l2.find(f2) + len(f2) + 1 :].split(".")[0].strip()
        info["au3_f"] = ""
        info["au3_l"] = ""
        info["num"] = 2
    else:
        f1 = info["cite"].split("et al.")[0].strip()
        info["au1_f"] = f1
        info["au1_l"] = bib[bib.find(f1) + len(f1) + 1 :].split(".")[0].strip()
        l2 = bib[bib.find(f1) + len(f1) + 1 :]
        f2 = l2.split(",")[1].strip()
        info["au2_f"] = f2
        l3 = l2[l2.find(f2) + len(f2) + 1 :]
        info["au2_l"] = l3.split(".")[0].strip()
        l4 = l3[l3.find(",") + 1 :].strip()
        if l4.strip().startswith("\\&"):
            l5 = l4[l4.find("\\&") + 3 :]
            f3 = l5.split(",")[0].strip()
            l6 = l5[l5.find(f3) + len(f3) + 1 :]
            info["au3_f"] = f3
            info["au3_l"] = l6.split(".")[0].strip()
            info["num"] = 3
        else:
            f3 = l4.split(",")[0].strip()
            info["au3_f"] = f3
            l5 = l4[l4.find(f3) + len(f3) + 1 :]
            info["au3_l"] = l5.split(".")[0].strip()
            info["num"] = 4
    info["au1_f_low"] = info["au1_f"].lower()
    info["au1_l_low"] = info["au1_l"].lower()
    info["au2_f_low"] = info["au2_f"].lower()
    info["au2_l_low"] = info["au2_l"].lower()
    info["au3_f_low"] = info["au3_f"].lower()
    info["au3_l_low"] = info["au3_l"].lower()
    return info


def read_content_dict(content_dict: dict, filename):
    """Read content dict from filename.

    A empty content_dict should be created before
    Each value is composed of a two element list of content_before(bib) and content_after(bib), which be "" if not the main file

    It will iterate through the import command

    Args:
        content_dict (dict): initial empty content_dict
        filename (Path): main tex filename
    """
    content_before = list()
    content_after = list()
    with open(filename) as f:
        before = True
        after = False
        for line in f:
            if before:
                content_before.append(line)
            if "\\begin{thebibliography}" in line:
                before = False
            if "\\end{thebibliography}" in line:
                after = True
            if "\\import" in line:
                line_split = re.split("{|}", line)
                import_filename = Path(
                    line_split[1], "{0}.tex".format(line_split[3])
                ).absolute()
                read_content_dict(content_dict, str(import_filename))
            if "\\include{" in line:
                line_split = re.split("{|}", line)
                import_filename = Path("{0}.tex".format(line_split[1])).absolute()
                read_content_dict(content_dict, str(import_filename))
            if after:
                content_after.append(line)
    content_dict[filename] = [content_before, content_after]


def drop_dup_key(df: pd.DataFrame) -> None:
    """Drop the duplicate keys.

    Args:
        df (pd.DataFrame): data
    """
    df.drop_duplicates("key", inplace=True)


def change_dup_cite(df: pd.DataFrame) -> None:
    """Change the duplicate cites.

    Ordered by the key and add a, b, c ... at the end of year in cite

    Args:
        df (pd.DataFrame): data
    """
    cite_dups = Counter(df.loc[df.duplicated("cite")]["cite"].values).keys()
    for cite in cite_dups:
        df_dup = df.loc[df["cite"] == cite]
        df_dup.sort_values(
            [
                "au1_f_low",
                "au1_l_low",
                "au2_f_low",
                "au2_l_low",
                "au3_f_low",
                "au3_l_low",
                "num",
                "year",
            ],
            inplace=True,
        )
        logger.info(
            "{0} duplicate cites {1} are found: {2}".format(
                len(df_dup), cite, ", ".join(df_dup.key)
            )
        )
        for i in range(len(df_dup)):
            item = df_dup.iloc[i]
            if re.search("[1-3][0-9]{3}[a-z]", item.cite) is None:
                year_re = re.search("[1-3][0-9]{3}", item.cite)  # Search for year
                if hasattr(year_re, "span"):
                    df.at[df_dup.index[i], "cite"] = (
                        item["cite"][: year_re.span()[1]]  # type: ignore
                        + chr(97 + i)
                        + item["cite"][year_re.span()[1] :]  # type: ignore
                    )  # Add a, b, c
            if re.search("[1-3][0-9]{3}[a-z]", item.bib) is None:
                year_re = re.search("[1-3][0-9]{3}", item.bib)
                if hasattr(year_re, "span"):
                    df.at[df_dup.index[i], "bib"] = (
                        item["bib"][: year_re.span()[1]]  # type: ignore
                        + chr(97 + i)
                        + item["bib"][year_re.span()[1] :]  # type: ignore
                    )
    df.drop_duplicates("cite", keep=False, inplace=True)
    df.reset_index(inplace=True, drop=True)


def sort_key(df: pd.DataFrame):
    """Sort the key.

    In the order of first author's first name, last name, ..., total num, year

    Args:
        df (pd.DataFrame): bib data
    """
    df.sort_values(
        [
            "au1_f_low",
            "au1_l_low",
            "au2_f_low",
            "au2_l_low",
            "au3_f_low",
            "au3_l_low",
            "num",
            "year",
        ],
        inplace=True,
    )
    df.reset_index(inplace=True, drop=True)


def merge_content_dict_to_line_list(content_dict: dict) -> list:
    """Merge content dict to line list.

    Args:
        content_dict (dict): content dict

    Returns:
        line_list (list): line list
    """
    line_list = list()
    for content in content_dict.values():
        line_list.extend([line for line in content[0] if not line.startswith("%")])
        line_list.extend([line for line in content[1] if not line.startswith("%")])
    return line_list


def remove_useless(df: pd.DataFrame, line_list: list) -> None:
    """Remove the bibs don't appear in the content.

    Args:
        df (DataFrame): bib data
        line_list (list): line list
    """
    content_join = "".join([line.strip() for line in line_list])
    useless = list()
    for i in range(len(df)):
        key = df.iloc[i].key
        if key not in content_join:
            logger.info("No citation of {0} is found!".format(key))
            useless.append(df.index[i])
    for index in useless:
        df.drop(index, inplace=True)
    df.reset_index(inplace=True, drop=True)


def find_missing(df: pd.DataFrame, line_list: list[str]) -> None:
    """Find missing keys in the content.

    Args:
        df (pd.DataFrame): bib data
        line_list (list): line list
    """
    content_join = "".join([line.strip() for line in line_list])
    keys = list()
    for item in re.findall(r"(?<=\{)[^\{\}]*(?=\})", content_join):
        if len(item) > 19:
            item_split = item.split(",")
            for i in range(len(item_split)):
                key = item_split[i].strip()
                if is_key(key) and key not in keys:
                    keys.append(key)
        else:
            key = item.strip()
            if is_key(key) and key not in keys:
                keys.append(key)
    missing_key = list()
    for key in keys:
        if key.strip() not in df.key.values:
            logger.info("{0} is not found in the bib!".format(key.strip()))
            missing_key.append(key.strip())
    missing_bibs = adsapi.export_citation(missing_key)
    if missing_bibs is not None:
        if len(missing_bibs) < len(missing_key):
            missing_key_found = list()
            for bib_item in missing_bibs:
                info = extract_info(bib_item)
                df.loc[len(df)] = info  # type: ignore
                missing_key_found.append(info["key"])
            missing_key_not_found = list(set(missing_key) - set(missing_key_found))
            for key in missing_key_not_found:
                logger.warning("{0} is not found in the ADS!".format(key))
        else:
            for bib_item in missing_bibs:
                df.loc[len(df)] = extract_info(bib_item)  # type: ignore


def is_key(key: str) -> bool:
    """Check whether input is a valid bibtex key.

    Args:
        key (str): input key string

    Returns:
        is_key (bool): whether input is a valid bibtex key
    """
    key = key.strip()
    if len(key) <= 5 or len(key) > 25:
        return False
    if len(key) != 19:
        return False
    if not key[:4].isdigit():
        return False
    if not key[-1].isupper():
        return False
    if key.startswith("fig:"):
        return False
    if key.startswith("sec:"):
        return False
    if key.startswith("tbl:"):
        return False
    if key[-4:].isdigit() and not key[-5].isdigit():
        return True
    return True


def write_tex(
    df: pd.DataFrame, content_dict: dict, main_file: Path, is_aas: bool
) -> None:
    """Write sorted tex to new file.

    Add suffix '_o' to the output filename

    Args:
        df (DataFrame): bib data
        content_dict (dict): content dict
        main_file (Path): main tex filename
        is_aas (bool): whether is aas format
    """
    content = content_dict[str(main_file)]
    aas_journal_dict = read_aas_journal_dict()

    filename_o = "{0}_o.tex".format(main_file.stem)
    with open(filename_o, "w") as f:
        for line in content[0]:
            f.write(line)
        for i in range(len(df)):
            item = df.iloc[i]
            bib_str = item.bib
            if not is_aas:
                split = bib_str.split(",")
                for j in range(len(split)):
                    if split[j].strip() in aas_journal_dict:
                        split[j] = " " + aas_journal_dict[split[j].strip()]
                    bib_str = ",".join(split)
            f.write("\\bibitem[{0}]{{{1}}}{2}\n".format(item.cite, item.key, bib_str))
        for line in content[1]:
            f.write(line)


def change_two_author_cite(df: pd.DataFrame) -> None:
    """Change two author cite format.

    Args:
        df (pd.DataFrame): bib data
    """
    df_sel = df[df.num == 2]
    df_sel["cite"] = df_sel.apply(_format_citation, axis=1)
    df.loc[df_sel.index, "cite"] = df_sel["cite"]


def _format_citation(row):
    return "{0} \\& {1}({2})".format(row["au1_f"], row["au2_f"], row["year"])


def check_arxiv(df: pd.DataFrame) -> None:
    """Check whether there is any arXiv ciatation.

    Args:
        df (pd.DataFrame): bib data
    """
    arxiv_list = list()
    for i in range(len(df)):
        if "arXiv" in df.iloc[i]["key"]:
            arxiv_list.append(df.iloc[i]["key"])
    if len(arxiv_list) > 0:
        logger.warning(
            "{0} arXiv citations in bib: {1}".format(
                len(arxiv_list), " ".join(arxiv_list)
            )
        )


def find_all_tex_files() -> list[str]:
    """Find all tex files in the current dicrectory.

    Returns:
        tex_files (list[str]): list of tex file name
    """
    tex_files = []
    start_dir = os.getcwd()
    pattern = "*.tex"
    for dir, _, _ in os.walk(start_dir):
        if ".backup" not in dir:
            tex_files.extend(glob.glob(os.path.join(dir, pattern)))
    return tex_files


def get_main_tex_file(filename):
    """Get main tex filename.

    Args:
        filename (str): input filename

    Return:
        filename (Path): absolute filename
    """
    if not filename:
        if filename is None:
            logger.info("No tex file is specified. Try to find one text file.")
        tex_files = find_all_tex_files()
        if len(tex_files) == 1:
            filename = Path(tex_files[0])
        else:
            if str(Path(os.getcwd(), "ms.tex")) in tex_files:
                filename = Path(os.getcwd(), "ms.tex")
            else:
                logger.warning(
                    "None or more than one tex files are found. Please specify one tex file!"
                )
                sys.exit()
    else:
        filename = Path(os.getcwd(), filename)
    logger.info(f"Found {filename}")
    return filename


def check_main_file_exist(main_file: Path) -> None:
    """Check main file exist.

    Args:
        main_file (Path): main tex file
    """
    if not main_file.is_file():
        logger.error("File not Found!")
        sys.exit()


def replace_file(main_file: Path) -> None:
    """Replace initial file.

    Args:
        main_file (Path): main tex file
    """
    Path("{0}_o.tex".format(main_file.stem)).rename(main_file)


def remove_doi(df: pd.DataFrame) -> None:
    """Remove doi info in the data.

    Args:
        df (pd.DataFrame): bib data frame
    """
    for i in range(len(df)):
        item = df.iloc[i]
        df.loc[i, "bib"] = item.bib.split(" doi:")[0]


def locate_bib(content_dict: dict[str, list], main_file: Path) -> str | None:
    """Locate bib file.

    Args:
        content_dict (dict): content dictionary
        main_file (Path): path of the main tex file

    Returns:
        bib_file (str): bib file path. If not found, return None.
    """
    for line in content_dict[str(main_file)][0]:
        if "\\addbibresource" in line:
            return line.split("{")[1].split("}")[0]
    return None


def query_bib_to_file(df: pd.DataFrame, bib_file: str, is_aas: bool) -> None:
    """Qurey bib and export file.

    Args:
        df (DataFrame): bib data
        bib_file (str): bib file path
        is_aas (bool): whether is aas format
    """
    bib_str = adsapi.export_citation(list(df.key.values), "bibtex")
    assert bib_str is not None
    aas_journal_dict = read_aas_journal_dict()
    with open(bib_file, "w") as f:
        for line in bib_str:
            if not is_aas and line.strip().startswith("journal"):
                split = re.split("{|}", line)
                if split[1] in aas_journal_dict:
                    split[1] = aas_journal_dict[split[1]]
                    line = split[0] + "{" + split[1] + "}" + split[2]
                else:
                    logger.warning(
                        "{0} is not found in the AAS journal TeX!".format(split[1])
                    )
            f.write(line + "\n")


def read_aas_journal_dict() -> dict:
    """Read AAS journel shortname dictionary."""
    with open(Path(os.environ["pub"], "aas_journal.cls"), "r") as f:
        aas_journal_dict = dict()
        for line in f:
            if "newcommand" in line:
                split = re.split("newcommand|{|}", line)
                aas_journal_dict[split[1].strip()] = split[3].strip()
    return aas_journal_dict


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filename", type=str, help="filename of main tex file")
    parser.add_argument("-d", "--doi", help="keep doi", action="store_true")
    parser.add_argument(
        "-r", "--replace", help="replace original file", action="store_true"
    )
    parser.add_argument("-b", "--bib", help="use bib file", action="store_true")
    parser.add_argument("-a", "--aas", help="not in aastex env", action="store_false")
    args = parser.parse_args()
    filename = args.filename

    main_file = get_main_tex_file(filename)
    check_main_file_exist(main_file)

    df = read_bib(main_file)
    content_dict = dict()
    read_content_dict(content_dict, str(main_file))
    line_list = merge_content_dict_to_line_list(content_dict)
    remove_useless(df, line_list)
    find_missing(df, line_list)
    check_arxiv(df)
    change_two_author_cite(df)
    drop_dup_key(df)
    change_dup_cite(df)
    sort_key(df)
    if not args.doi:
        remove_doi(df)
    if not args.bib:
        write_tex(df, content_dict, main_file, args.aas)
        if args.replace:
            replace_file(main_file)
    else:
        bib_file = locate_bib(content_dict, main_file)
        if bib_file is not None:
            query_bib_to_file(df, bib_file, args.aas)
