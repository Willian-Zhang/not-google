import warc
import sys
import argparse
from tqdm import tqdm

# Options
parser = argparse.ArgumentParser(description='Extract Lexicons from WETs')
parser.add_argument('files', metavar='<filepath>', nargs='+',
                    help='path to file')

args = parser.parse_args()

for filepath in args.files:
    print("* Dealing:", filepath, file=sys.stderr)
    with warc.open(filepath, 'rb') as f:
        for record in tqdm(f, unit='records'):
            pass
