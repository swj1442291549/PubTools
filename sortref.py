import re
import pandas as pd
from collections import Counter


def read_bib(filename):
    """Read bib from the tex file

    separate the bibitem into cite, key, bib

    "\bibitem[cite]{key} bib"


    Args:
        filename (string): file name

    Returns:
        df (DataFrame): bib data
    """
    cite = list()
    key = list()
    bib = list()
    with open(filename) as f:
        bib_tag = False
        for line in f:
            if '\\end{thebibliography}' in line:
                bib_tag = False
            if bib_tag == True:
                if line.strip() != '':
                    item = line.strip()
                    cite.append(item.split('\\bibitem[')[1].split(']')[0])
                    key.append(
                        item.split('\\bibitem[')[1].split(']')[1].split('{')[1]
                        .split('}')[0])
                    bib.append(
                        item.split('\\bibitem[')[1].split(']')[1][item.split(
                            '\\bibitem[')[1].split(']')[1].find('}') + 1:]
                        .strip())
            if '\\begin{thebibliography}' in line:
                bib_tag = True
    df = pd.DataFrame({'cite': cite, 'key': key, 'bib': bib})
    pd.options.mode.chained_assignment = None

    # Read the year
    year = [int(item[:4]) for item in df.key.values]
    df = df.assign(year=year)
    # Read the first author
    au1_f = list()
    au1_l = list()
    au2_f = list()
    au2_l = list()
    au3_f = list()
    au3_l = list()
    num = list()
    for i in range(len(df)):
        item = df.iloc[i]
        bib = item.bib[:item.bib.find(item.key[:4])]
        if 'et al.' not in item.cite and '\&' not in item.cite:
            f = item.cite.split('(')[0].strip()
            au1_f.append(f)
            au1_l.append(bib[bib.find(f) + len(f) + 1:].split('.')[0].strip())
            au2_f.append('')
            au2_l.append('')
            au3_f.append('')
            au3_l.append('')
            num.append(1)
        elif '\&' in item.cite and 'et al.' not in item.cite:
            f1 = item.cite.split('\&')[0].strip()
            au1_f.append(f1)
            au1_l.append(bib[bib.find(f1) + len(f1) + 1:].split('.')[0].strip())
            f2 = item.cite.split('\&')[1].split('(')[0].strip()
            au2_f.append(f2)
            l2 = bib[bib.find(f1) + len(f1) + 1:]
            au2_l.append(l2[l2.find(f2) + len(f2) + 1:].split('.')[0].strip())
            au3_f.append('')
            au3_l.append('')
            num.append(2)
        else:
            f1 = item.cite.split('et al.')[0].strip()
            au1_f.append(f1)
            au1_l.append(bib[bib.find(f1) + len(f1) + 1:].split('.')[0].strip())
            l2 = bib[bib.find(f1) + len(f1) + 1:]
            f2 = l2.split(',')[1].strip()
            au2_f.append(f2)
            l3 = l2[l2.find(f2) + len(f2) + 1:]
            au2_l.append(l3.split('.')[0].strip())
            l4 = l3[l3.find(',') + 1:].strip()
            if l4.strip().startswith('\\&'):
                l5 = l4[l4.find('\\&') + 3:]
                f3 = l5.split(',')[0].strip()
                l6 = l5[l5.find(f3) + len(f3) + 1:]
                au3_f.append(f3)
                au3_l.append(l6.split('.')[0].strip())
                num.append(3)
            else:
                f3 = l4.split(',')[0].strip()
                au3_f.append(f3)
                l5 = l4[l4.find(f3) + len(f3) + 1:]
                au3_l.append(l5.split('.')[0].strip())
                num.append(4)
    df = df.assign(au1_f=au1_f)
    df = df.assign(au1_l=au1_l)
    df = df.assign(au2_f=au2_f)
    df = df.assign(au2_l=au2_l)
    df = df.assign(au3_f=au3_f)
    df = df.assign(au3_l=au3_l)
    df = df.assign(num=num)
    return df


def read_content(filename):
    """Read content from the file
    
    Args:
        filename (string): file name

    Returns:
        content_before (list): line before the bib
        content_after (list): line after the bib
    """
    content_before = list()
    content_after = list()
    with open(filename) as f:
        before = True
        after = False
        for line in f:
            if before:
                content_before.append(line)
            if '\\begin{thebibliography}' in line:
                before = False
            if '\\end{thebibliography}' in line:
                after = True
            if after:
                content_after.append(line)
    return content_before, content_after


def drop_dup_key(df):
    """Drop the duplicate keys

    Args:
        df (DataFrame): data
    """
    df.drop_duplicates('key', inplace=True)


def change_dup_cite(df):
    """Change the duplicate cites

    Ordered by the key and add a, b, c ... at the end of year in cite

    Args:
        df (DataFrame): data

    Returns:
        df (DataFrame): data
    """
    cite_dups = Counter(df[df.duplicated('cite') == True]['cite'].values).keys()
    for cite in cite_dups:
        df_dup = df[df['cite'] == cite]
        df_dup.sort_values('key', inplace=True)
        print('{0} duplicate cites {1} are found: {2}'.format(len(df_dup), cite, ', '.join(df_dup.key)))
        for i in range(len(df_dup)):
            item = df_dup.iloc[i]
            year_re = re.search('[1-3][0-9]{3}', item.cite)  # Search for year
            if hasattr(year_re, 'span'):
                df.at[df_dup.index[i], 'cite'] = item['cite'][:year_re.span(
                )[1]] + chr(97 + i) + item['cite'][year_re.span()
                                                   [1]:]  # Add a, b, c
    df.drop_duplicates('cite', keep=False, inplace=True)
    df.reset_index(inplace=True, drop=True)


def sort_key(df):
    """Sort the key
    
    In the order of first author's first name, last name, ..., total num, year

    Args:
        df (DataFrame): bib data
    """
    df.sort_values(
        ['au1_f', 'au1_l', 'au2_f', 'au2_l', 'au3_f', 'au3_l', 'num', 'year'],
        inplace=True)
    df.reset_index(inplace=True, drop=True)


def remove_useless(df, content):
    """Remove the bibs don't appear in the content
    
    Args:
        df (DataFrame): bib data
        content (list): content

    """
    content_join = "".join(content[0])
    useless = list()
    for i in range(len(df)):
        key = df.iloc[i].key
        if key not in content_join:
            print('No citation of {0} is found!'.format(key))
            useless.append(df.index[i])
    for index in useless:
        df.drop(index, inplace=True)
    df.reset_index(inplace=True, drop=True)



def write_tex(df, content, filename):
    """Write sorted tex to new file
    
    Add suffix '_o' to the output filename 

    Args:
        df (DataFrame): bib data
        content (list): content
    """
    filename_o = '{0}_o.tex'.format(filename[: filename.find('.tex')])
    with open(filename_o, 'w') as f:
        for line in content[0]:
            f.write(line)
        for i in range(len(df)):
            item = df.iloc[i]
            f.write('\\bibitem[{0}]{{{1}}}{2}\n'.format(item.cite, item.key, item.bib))
        for line in content[1]:
            f.write(line)


if __name__ == "__main__":
    # filename = 'ms.tex'
    filename = 'proposal.tex'
    df = read_bib(filename)
    content = read_content(filename)
    remove_useless(df, content)
    drop_dup_key(df)
    change_dup_cite(df)
    sort_key(df)
    write_tex(df, content, filename)
