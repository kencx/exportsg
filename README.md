# exportSG

Export SG bank statements from PDF to CSV. Supported banks:

- DBS/POSB
- [ ] UOB
- [ ] OCBC
- [ ] SCB

## Install
Python <=3.10

```bash
$ python3 -m pip install -r requirements.txt
```

Tkinter is also required. You may need to install it separately on certain
Linux distributions.

```bash
$ pacman -S tk imagemagick
```

## Usage

```bash
$ ./main.py -f FILE.pdf [--visualize true]
```
