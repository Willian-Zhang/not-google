import argparse

# Options
parser = argparse.ArgumentParser(description='Test (UUID not supported)')
parser.add_argument('files', metavar='<filepath>', nargs='+',
                    help='path to file')
parser.add_argument('-b','--binary', action='store_true',
                    help='output docID and freqauncy as binary form')
parser.add_argument('-s','--startID', metavar='<number>', type=int, default=0,
                    help='Starting ID for docID Assigment')

parser.add_argument('--skipChinese', action='store_true',
                    help='if set, will not parse chinese words')
args = parser.parse_args()

for filepath in args.files:
    with open(filepath, mode='rb') as f:
        i = 1
        prevLine=None
        for line in f.readlines():
            try:
                (word, doc) = line.split(b'\t')
                word.decode()
            except Exception as e:
                print(e, i)
                print(prevLine)
                print(line)
            finally:
                i+=1
                prevLine = line

        