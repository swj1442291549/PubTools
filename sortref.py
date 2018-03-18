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
    cite= list()
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
                    key.append(item.split('\\bibitem[')[1].split(']')[1].split('{')[1].split('}')[0])
                    bib.append(item.split('\\bibitem[')[1].split(']')[1].split('}')[1].strip())
            if '\\begin{thebibliography}' in line:
                bib_tag = True
    df = pd.DataFrame({'cite': cite, 'key': key, 'bib': bib})
    pd.options.mode.chained_assignment = None
    return df


def drop_duplicates(df):
    df.drop_duplicates('key', inplace=True)


if __name__ == "__main__":
    filename = 'proposal.tex'
    df = read_bib(filename)
    drop_duplicates(df)

    cite_dups = Counter(df[df.duplicated('cite') == True]['cite'].values).keys()
    for cite in cite_dups:
        df_dup = df[df['cite'] == cite]
        df_dup.sort_values('key', inplace=True)
    



