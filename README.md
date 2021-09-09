# PubTools
Tools for Publication

## SortRef
Sort the reference list with `thebibliography` environment

### Usage
```bash
python sortref.py filename
```

It will then generate a file with suffix 'o' 

### Error
While running, it will throw some error or warning messages. Be sure to deal with these messages.

## Remove CTRL-M characters from a file
```bash
sed -e "s///" ms.tex > msn.tex
```
To enter ``, type `CTRL-V`, `CTRL-M`
