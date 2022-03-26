import os
import re
import sys
import glob
import logging
import argparse

from pathlib import Path
from collections import Counter

import pandas as pd

import adsapi


def read_bib(filename):
    """Read bib from the tex file

    separate the bibitem into cite, key, bib

    "\bibitem[cite]{key} bib"

    Args:
        filename (string): file name

    Returns:
        df (DataFrame): bib data
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
            if bib_tag == True:
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
    pd.options.mode.chained_assignment = None
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


def extract_info(bib_item):
    """Extract info from bib_item

    Args:
        bib_item (string): bib item

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
    item = pd.Series(info)
    info["year"] = item.key[:4]
    bib = item.bib[: item.bib.find(info["year"])]
    if "et al." not in item.cite and "\&" not in item.cite:
        f = item.cite.split("(")[0].strip()
        info["au1_f"] = f
        info["au1_l"] = bib[bib.find(f) + len(f) + 1 :].split(".")[0].strip()
        info["au2_f"] = ""
        info["au2_l"] = ""
        info["au3_f"] = ""
        info["au3_l"] = ""
        info["num"] = 1
    elif "\&" in item.cite and "et al." not in item.cite:
        f1 = item.cite.split("\&")[0].strip()
        if f1[-1] == ",":
            f1 = f1[:-1]
        info["au1_f"] = f1
        info["au1_l"] = bib[bib.find(f1) + len(f1) + 1 :].split(".")[0].strip()
        f2 = item.cite.split("\&")[1].split("(")[0].strip()
        l2 = bib[bib.find(f1) + len(f1) + 1 :]
        info["au2_f"] = f2
        info["au2_l"] = l2[l2.find(f2) + len(f2) + 1 :].split(".")[0].strip()
        info["au3_f"] = ""
        info["au3_l"] = ""
        info["num"] = 2
    else:
        f1 = item.cite.split("et al.")[0].strip()
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


def read_content_dict(content_dict, filename):
    """Read content dict from filename

    A empty content_dict should be created before
    Each value is composed of a two element list of content_before(bib) and content_after(bib), which be "" if not the main file

    It will iterate through the \import command

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


def drop_dup_key(df):
    """Drop the duplicate keys

    Args:
        df (DataFrame): data
    """
    df.drop_duplicates("key", inplace=True)


def change_dup_cite(df):
    """Change the duplicate cites

    Ordered by the key and add a, b, c ... at the end of year in cite

    Args:
        df (DataFrame): data
    """
    cite_dups = Counter(df[df.duplicated("cite") == True]["cite"].values).keys()
    for cite in cite_dups:
        df_dup = df[df["cite"] == cite]
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
        logging.info(
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
                        item["cite"][: year_re.span()[1]]
                        + chr(97 + i)
                        + item["cite"][year_re.span()[1] :]
                    )  # Add a, b, c
            if re.search("[1-3][0-9]{3}[a-z]", item.bib) is None:
                year_re = re.search("[1-3][0-9]{3}", item.bib)
                if hasattr(year_re, "span"):
                    df.at[df_dup.index[i], "bib"] = (
                        item["bib"][: year_re.span()[1]]
                        + chr(97 + i)
                        + item["bib"][year_re.span()[1] :]
                    )
    df.drop_duplicates("cite", keep=False, inplace=True)
    df.reset_index(inplace=True, drop=True)


def sort_key(df):
    """Sort the key

    In the order of first author's first name, last name, ..., total num, year

    Args:
        df (DataFrame): bib data
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


def merge_content_dict_to_line_list(content_dict):
    line_list = list()
    for content in content_dict.values():
        line_list.extend([line for line in content[0]])
        line_list.extend([line for line in content[1]])
    return line_list


def remove_useless(df, line_list):
    """Remove the bibs don't appear in the content

    Args:
        df (DataFrame): bib data
        line_list (list): line list
    """
    content_join = "".join([line.strip() for line in line_list])
    useless = list()
    for i in range(len(df)):
        key = df.iloc[i].key
        if key not in content_join:
            logging.info("No citation of {0} is found!".format(key))
            useless.append(df.index[i])
    for index in useless:
        df.drop(index, inplace=True)
    df.reset_index(inplace=True, drop=True)


def find_missing(df, line_list):
    """Find missing keys in the content

    Args:
        df (DataFrame): bib data
        line_list (list): line list
    """
    content_join = "".join([line.strip() for line in line_list])
    keys = list()
    for item in re.findall("(?<=\{)[^\{\}]*(?=\})", content_join):
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
            logging.info("{0} is not found in the bib!".format(key.strip()))
            missing_key.append(key.strip())
    missing_bibs = adsapi.export_citation(missing_key)
    if missing_bibs is not None:
        if len(missing_bibs) < len(missing_key):
            missing_key_found = list()
            for bib_item in missing_bibs:
                info = extract_info(bib_item)
                df.loc[len(df)] = info
                missing_key_found.append(info["key"])
            missing_key_not_found = list(set(missing_key) - set(missing_key_found))
            for key in missing_key_not_found:
                logging.warning("{0} is not found in the ADS!".format(key))
        else:
            for bib_item in missing_bibs:
                df.loc[len(df)] = extract_info(bib_item)


def is_key(key):
    key = key.strip()
    if len(key) <= 5 or len(key) > 25:
        return False
    if key[-4:].isdigit() and not key[-5].isdigit():
        return True
    if len(key) != 19:
        return False
    if not key[:4].isdigit():
        return False
    if not key[-1].isupper():
        return False
    return True


def write_tex(df, content_dict, main_file, is_aas):
    """Write sorted tex to new file

    Add suffix '_o' to the output filename

    Args:
        df (DataFrame): bib data
        content_dict (dict): content dict
        main_file (Path): main tex filename
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


def change_two_author_cite(df):
    df_sel = df[df.num == 2]
    for i in range(len(df_sel)):
        item = df_sel.iloc[i]
        df.loc[item.name, "cite"] = "{0} \& {1}({2})".format(
            item.au1_f, item.au2_f, item.year
        )


def check_arxiv(df):
    """Check whether there is any arXiv ciatation

    Args:
        df (DataFrame): bib data
    """
    arxiv_list = list()
    for i in range(len(df)):
        if "arXiv" in df.iloc[i]["key"]:
            arxiv_list.append(df.iloc[i]["key"])
    if len(arxiv_list) > 0:
        logging.warning(
            "{0} arXiv citations in bib: {1}".format(
                len(arxiv_list), " ".join(arxiv_list)
            )
        )


def find_all_tex_files():
    tex_files = []
    start_dir = os.getcwd()
    pattern = "*.tex"
    for dir, _, _ in os.walk(start_dir):
        if ".backup" not in dir:
            tex_files.extend(glob.glob(os.path.join(dir, pattern)))
    return tex_files


def get_main_tex_file(filename):
    """Get main tex filename

    Args:
        filename (str): input filename

    Return:
        filename (Path): absolute filename
    """
    if not filename:
        if filename is None:
            logging.info("No tex file is specified. Try to find one text file.")
        if len(tex_files) == 1:
            filename = Path(tex_files[0])
        else:
            if str(Path(os.getcwd(), "ms.tex")) in tex_files:
                filename = Path(os.getcwd(), "ms.tex")
            else:
                logging.warning(
                    "None or more than one tex files are found. Please specify one tex file!"
                )
                sys.exit()
    else:
        filename = Path(os.getcwd(), filename)
    return filename


def check_main_file_exist(main_file):
    if not main_file.is_file():
        logging.error("File not Found!")
        sys.exit()


def replace_file(main_file):
    Path("{0}_o.tex".format(main_file.stem)).rename(main_file)


def remove_doi(df):
    for i in range(len(df)):
        item = df.iloc[i]
        df.loc[i, "bib"] = item.bib.split(" doi:")[0]


def locate_bib(content_dict, main_file):
    for line in content_dict[str(main_file)][0]:
        if "\\addbibresource" in line:
            return line.split("{")[1].split("}")[0]
    return False


def query_bib_to_file(df, bib_file, is_aas):
    bib_str = adsapi.export_citation(list(df.key.values), "bibtex")
    aas_journal_dict = read_aas_journal_dict()
    with open(bib_file, "w") as f:
        for line in bib_str:
            if not is_aas and line.strip().startswith("journal"):
                split = re.split("{|}", line)
                if split[1] in aas_journal_dict:
                    split[1] = aas_journal_dict[split[1]]
                    line = split[0] + "{" + split[1] + "}" + split[2]
                else:
                    logging.warning(
                        "{0} is not found in the AAS journal TeX!".format(split[1])
                    )
            f.write(line + "\n")


def read_aas_journal_dict():
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

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    tex_files = find_all_tex_files()
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
        query_bib_to_file(df, bib_file, args.aas)
