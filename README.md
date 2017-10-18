# Inverted Index (II)
Build Inverted Index upon wet file

### Table of contents
* [Inverted Index (II)](#inverted-index-(ii))
* [Features](#features)
* [How to run](#how-to-run)
  * [Requirements](#requirements)
  * [Installation](#installation)
  * [Recommand for running](#recommand-for-running)
    * [Virtual env](#virtual-env)
* [For the first time:](#for-the-first-time:)
  * [Run](#run)
    * [Example usage](#example-usage)
      * [Lexicon extraction](#lexicon-extraction)
      * [Sort Merging](#sort-merging)
    * [Actual usage](#actual-usage)
  * [Notes on Running on Servers](#notes-on-running-on-servers)
    * [HPC](#hpc)
      * [Load Python 3 module](#load-python-3-module)
* [Future Work](#future-work)
  * [Distributed](#distributed)
* [Development](#development)

# Features
* Language detection
* Chinese support along with latin-charactor based languages
* Binary I/O and Stroage
* Progress display

# How to run
## Requirements
* Python 3.4+

## Installation
Please consider the [Recommand for running](#recommand-for-running) section before  Installation. 

If you insist to install directly, It will be okey.

``` bash
$ pip install -r requirements.txt
```

### Recommand for running
It is recommanded to use virtual environment for python packages to avoid package conflicts.
#### Virtual env
For the first time of for this project, start a new venv from as:

``` bash
$ pyvenv .env
```

And then or for later use, activate it:

``` bash
$ source .env/bin/activate
# For the first time:
$ pip install -r requirements.txt
```


## Usage
The running of the whole inverted index building has been devided into 3 parts:
* Download wet files
* Lexicon extraction
* Sort Merging 

For the first **Lexicon extraction** stage, use python script `extract_lex`, and for **Sort Merging** stage use `merge.py`

### Example usage
#### Download wet files
``` bash
$ ./scripts/dl.sh 100 
```
This will download `100` wet files to `data/wet`. (change `100` to get more or less)
#### Lexicon extraction
``` bash
$ python extract_lex.py --urlTable "data/url-table.tsv" data/wet/*.warc.wet.gz | sort > "data/all.lex" 
```
This will extract all lexicons (that in language English, French, Germany, Italian, Latin, Spanish and Chinese) from the `wet` files in `data/wet/`, and write the sorted lexicons to `data/all.lex`.
#### Sort Merging
``` bash
$ cat  "data/all.lex" | python merge.py > "data/inverted-index.ii"
```
This will read all **sorted** lexicons, merge them into inverted lists and write to `data/inverted-index.ii`.
### Actual usage
Example usage is not practical when you wants to:

* Run on many wet files
* Use binary for performance boost

So there are smarter version provided for these needs:

``` bash
# extract all wet files in `data/wet`
$ ./scripts/extract-all.sh 
* Dealing: data/wet/CC-MAIN-20170919112242-20170919132242-00000.warc.wet.gz
Building prefix dict from the default dictionary ...
Loading model from cache /var/folders/dy/dh2zyqj93fg72s9z4w2tnwy00000gn/T/jieba.cache
Loading model cost 0.828 seconds.
Prefix dict has been built succesfully.
40919records [05:00, 136.23records/s]
...
$ ./scripts/merge.sh
```
`extract-all.sh` will individually extract and sort lexicons into fex files to `data/lex`.

`merge.sh` will take all **sorted** lex files and merge them into the final II file `data/inverted-index.ii`.

All oprations are done in binary.


## Notes on Running on Servers
Scripts are created for copying necessary exectables to server. Use of example:

``` bash
$ ./scripts/deploy.sh user@server:path
```
# How it works
![Sturcture](https://github.com/Willian-Zhang/inverted-index/raw/master/miscellaneous/Structure.png)

### HPC
Distributed version of this II building program is not completed, you will not be able to use it on Hadoop or Spark or Hive. However you could use HPC as ordinary server to run the program. 

There were works done for prepration of this program to be distributable. Please read [Future Work > Distributed](#distributed) section.

#### Load Python 3 module
``` bash
$ module load python
```

# Future Work 
## Distributed

# Development
Add new requirements if new python packages are used

``` bash
$ pip freeze > requirements.txt
```

If to Change of README.md file. There is a ruby script to build Markdown Table of Content:

``` bash
$ruby scripts/generate_toc.rb
```