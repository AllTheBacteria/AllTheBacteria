# sketchlib

OSF component page: https://osf.io/rceq5/

## Release 0.2 and incremental release 202408

Version 0.1.0 of sketchlib was run, with command like:

```
sketchlib sketch -f file_list.txt -k 17 -s 1024 -o atb_sketchlib_v020 --threads 32 
```


## Incremental release 202505

Version 0.2.4 of sketchlib was used. An index of just release 202505 was made with:

```
sketchlib sketch -f file_list.txt -k 17 -s 1024 -o atb_sketchlib.202505 --threads 32
```

A complete aggregated index of release 0.2 plus incremental releases 202408 and
202505 was made by adding the new `atb_sketchlib.202505` to the existing aggregated
index `atb_sketchlib.aggregated.202408`:

```
sketchlib merge -o atb_sketchlib.aggregated.202505 atb_sketchlib.aggregated.202408.skd atb_sketchlib.202505.skd
```


