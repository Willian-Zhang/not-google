# Recommanded

## virtual env
### Use virtual env
``` bash
source .env/bin/activate
```
or for the first time:
``` bash
pyvenv .env
```
### Install requirements
``` bash
pip install -r requirements.txt
```

## HPC
### Activate Python 3
``` bash
module load python
```

# Dev
### Add new requirements
``` bash
pip freeze > requirements.txt
```