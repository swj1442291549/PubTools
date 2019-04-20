import ads
import pandas as pd


def export_aastex(bibcodes):
    """Export the bibcodes in the form of aastex 

    Args:
        bibcodes (list): string list of bibcodes

    Returns:
        bibs (list): string list of bibs
    """
    if len(bibcodes) == 0:
        return []
    else:
        q = ads.ExportQuery(bibcodes, format='aastex')
        try:
            export_response = q.execute()
        except:
            print('{0} is not in ADS library!'.format(bibcodes))
        else:
            bibs = list()
            for bib in export_response.split('\n'):
                if len(bib) > 0:
                    bibs.append(bib)
            return bibs


