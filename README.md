# exportSG

Export SG bank statements from PDF to CSV. Supported banks:

- [x] DBS/POSB
- [x] UOB
- [ ] OCBC
- [ ] SCB

## Usage

```bash
# write POSB statement to csv
$ ./main.py -p FILE.pdf -f output.csv

# visualize pdf
$ ./main.py -p FILE.pdf -v
```

### Read CSV

```bash
$ pacman -S xsv
$ xsv table output.csv

# exclude DESCRIPTION column
$ xsv select '!2' output.csv | xsv table
```

## Development
Python <=3.10

```bash
$ python3 -m pip install -r requirements.txt
```

Tkinter is also required. You may need to install it separately on certain
Linux distributions.

```bash
$ pacman -S tk imagemagick
```
