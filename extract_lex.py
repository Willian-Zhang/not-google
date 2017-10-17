import warc
import sys, os
import re
from uuid import UUID
import argparse
import slugid
from collections import Counter

# NLP
from langid.langid import LanguageIdentifier, model
Language = LanguageIdentifier.from_modelstring(model, norm_probs=True)

import jieba

# Options
parser = argparse.ArgumentParser(description='Extract Lexicons from WETs')
parser.add_argument('files', metavar='<filepath>', nargs='+',
                    help='path to file')
parser.add_argument('-b','--binary', action='store_true',
                    help='output docID and freqauncy as binary form')
parser.add_argument('-s','--startID', metavar='<number>', type=int, default=0,
                    help='Starting ID for docID Assigment')


# UUID
parser.add_argument('-u','--uuid', action='store_true',
                    help='use UUID/ if not specified, use assign new ID mode')
parser.add_argument('-c','--compressuuid', action='store_true',
                    help='compress UUID in a compact form, only valid in UUID mode')


args = parser.parse_args()

# constants
space_devided_langs = ['en','fr','de','it','la','es']
latin_sep_words = r"\W+"
chinese_stop_words = ['，', '\n','。',',', '.' ,'？','|',']','！','（','）', ' ', '\t']
global_escape_words = [b'\x00']

from modules import NumberGenerator

docIDDigits = 4
frequancyDigits = 2
docIdGenerator = NumberGenerator.Number(digits = docIDDigits, start = args.startID)
for filepath in args.files:
    print("* Dealing:", filepath, file=sys.stderr)
    with warc.open(filepath, 'rb') as f:
        for record in f:
            URI = record.header.get('warc-target-uri')
            content = record.payload.read()
            if URI is not None and content is not None:
                lang = Language.classify(content)
                if lang[0] in space_devided_langs:
                    words = latin_sep_words.split(str(content))
                elif lang[0] == 'zh':
                    words = jieba.cut_for_search(content)
                    words = [word for word in words if word not in chinese_stop_words]
                else:
                    # other languages
                    continue

                words = [ word for word in words if word not in global_escape_words]
                words = [(k, v) for (k,v) in Counter(words).items()]

                if args.uuid:
                    uuid = record.header.get('WARC-Record-ID')[1:-1]
                    uuid = UUID(uuid)
                    if args.compressuuid:
                        uuid = slugid.encode(uuid)
                    [print("{word}\t{uuid}\{count}".format(
                            word=word, uuid=uuid.decode('ascii'), count= count
                            )) 
                        for (word, count) in words]
                else:
                    docID = docIdGenerator.next()
                    if args.binary:
                        docID = docID.to_bytes(docIDDigits,'little', signed=True)
                    else:
                        docID = str(docID)
                    for (word, count) in words: 
                        sys.stdout.write(word)
                        sys.stdout.write('\t')
                        if args.binary:
                            sys.stdout.buffer.write(docID)
                            sys.stdout.write('\t')
                            sys.stdout.buffer.write(count.to_bytes(frequancyDigits,'little', signed=True))
                        else:
                            sys.stdout.write(docID)
                            sys.stdout.write('\t')
                            sys.stdout.write(str(count))
                        sys.stdout.write('\n')
                            
