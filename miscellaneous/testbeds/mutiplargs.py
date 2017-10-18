import argparse

parser = argparse.ArgumentParser(description='Multiargs test')
parser.add_argument('files', metavar='filepath', nargs='+',
                    help='path to file')
parser.add_argument('-b','--binary', action='store_true',
                    help='sum the integers (default: find the max)')

args = parser.parse_args()

print(args.files)
print(args.binary)
