import warc
import sys, os
import re
from uuid import UUID
import argparse
import slugid
from collections import Counter
from tqdm import tqdm


# Options
parser = argparse.ArgumentParser(description='Extract Lexicons from WETs')
parser.add_argument('files', metavar='<filepath>', nargs='+',
                    help='path to file')
parser.add_argument('-b','--binary', action='store_true',
                    help='output docID as binary form')
parser.add_argument('-s','--startID', metavar='<number>', type=int, default=0,
                    help='docID Assigment starting after ID')

parser.add_argument('-T', '--urlTable', metavar='<filepath>',
                    help='if set, will append urlTable to file')
parser.add_argument('--bufferSize', metavar='<number>', type=int, default=100,
                    help='Buffer Size for URL Table Writing')

# UUID
parser.add_argument('-u','--uuid', action='store_true',
                    help='use UUID/ if not specified, use assign new ID mode')
parser.add_argument('-c','--compressuuid', action='store_true',
                    help='compress UUID in a compact form, only valid in UUID mode')


args = parser.parse_args()

latin_sep_words = re.compile(r"\W+")
latin_words_pattern = re.compile(r"\w+")

from modules import NumberGenerator

docIDDigits = 4
frequancyDigits = 2
docIdGenerator = NumberGenerator.Number(digits=docIDDigits, after=args.startID)

if args.urlTable:
    fileURLTable = open(args.urlTable, mode='a', buffering=args.bufferSize)

for filepath in args.files:
    print("* Dealing:", filepath, file=sys.stderr)
    with warc.open(filepath, 'rb') as f:
        for record in tqdm(f, unit='records'):
            URI = record.header.get('warc-target-uri')
            content = record.payload.read()
            if URI is not None and content is not None:
                words = latin_sep_words.split(str(content))

                words = [(k, v) for (k,v) in Counter(words).items()]

                if args.uuid:
                    uuid = record.header.get('WARC-Record-ID')[1:-1]
                    uuid = UUID(uuid)
                    if args.compressuuid:
                        uuid = slugid.encode(uuid)
                    [print("{word}\t{uuid} {count}".format(
                        word=word, uuid=uuid.decode('ascii'), count=count
                        ))
                     for (word, count) in words]
                else:
                    docID = docIdGenerator.next()
                    if args.urlTable:
                        print("{docID}\t{url}".format(docID=docID, url=URI)
                              , file=fileURLTable)
                        # fileURLTable.write("{docID}\t{url}\t{lan}".format(docID=docID, url=URI, lan=lang))
                    if args.binary:
                        docID = docID.to_bytes(docIDDigits, 'little', signed=True)
                    else:
                        docID = str(docID)
                    if args.binary:
                        for (word, count) in words: 
                            sys.stdout.buffer.write(word.encode() +
                                             b'\t' + docID + b' ' +
                                             str(count).encode() +
                                             b'\n')
                    else:
                        for (word, count) in words: 
                            print("{word}\t{docID} {count}".format(word=word, docID=docID, count=str(count))
                                , file = sys.stdout)
                            
if args.urlTable:
    fileURLTable.close()
