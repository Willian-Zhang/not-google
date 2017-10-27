import warc
import sys, os
import re
from uuid import UUID
import argparse
import slugid
from collections import Counter
from tqdm import tqdm

import redis

# Options
parser = argparse.ArgumentParser(description='Extract Lexicons from WETs')
parser.add_argument('files', metavar='<filepath>', nargs='+',
                    help='path to file')
parser.add_argument('-b','--binary', action='store_true',
                    help='output docID as binary form')
parser.add_argument('-s','--startID', metavar='<number>', type=int, default=0,
                    help='docID Assigment starting after ID')

parser.add_argument('--skipChinese', action='store_true',
                    help='if set, will not parse chinese words')

parser.add_argument('-r', '--redis', metavar='<path/to/redis.sock>', default='/tmp/redis.sock',
                    help='if set, will use redis server to store URL Table')
parser.add_argument('-db', '--redisDB', metavar='<dbID>', type=int, default=0,
                    help='The DB to use in redis server')
parser.add_argument('-w', '--docIDwet', metavar='<path/to/docIDwet.tsv>',
                    help='If set, direct docID to wet summery to file')
# UUID
parser.add_argument('-u','--uuid', action='store_true',
                    help='use UUID/ if not specified, use assign new ID mode')
parser.add_argument('-c','--compressuuid', action='store_true',
                    help='compress UUID in a compact form, only valid in UUID mode')

args = parser.parse_args()

if not args.skipChinese:
    import jieba


# NLP
from langid.langid import LanguageIdentifier, model
Language = LanguageIdentifier.from_modelstring(model, norm_probs=True)



# constants
space_devided_langs = ['en','fr','de','it','la','es']
latin_sep_words = re.compile(r"\W+")
# deprecated use non_latin_words_pattern
# chinese_stop_words = ['，', '\n','。',',', '.' ,'？','|',']','！','（','）', ' ', '\t']
# global_escape_words = [b'\x00']
non_latin_words_pattern = re.compile(r"([^\u0000-\u007F]|\w)+")

from modules import NumberGenerator

docIDDigits = 4
frequancyDigits = 2
docIdGenerator = NumberGenerator.Number(digits=docIDDigits, after=args.startID)

r = redis.Redis(unix_socket_path=args.redis, db=args.redisDB)
if args.docIDwet:
    docIDwetFile = open(args.docIDwet, mode='a')
else:
    docIDwetFile = sys.stderr

for filepath in args.files:
    print("* Dealing:", filepath, file=sys.stderr)
    with warc.open(filepath, 'rb') as f:
        for (record, offset, _) in tqdm(f.browse(), unit='records'):
            URI = record.url
            if URI:
                content = record.payload.read()
                if content:
                    (lang, langConfidence) = Language.classify(content)
                    if lang in space_devided_langs:
                        words = latin_sep_words.split(str(content))
                    elif lang == 'zh' and not args.skipChinese:
                        words = jieba.cut(content, cut_all=False)
                        # words = list(words)
                        words = [word for word in words if non_latin_words_pattern.match(word)]
                    else:
                        # other languages
                        continue

                    # words = [ word for word in words if word not in global_escape_words]
                    docLength = len(words)
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
                        r.hmset(docID, {
                            'url' : URI,
                            'lang': lang,
                            'len' : docLength,
                            'off' : offset
                        })

                        if args.binary:
                            docID = docID.to_bytes(docIDDigits, 'big', signed=True)
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
        # After each file:
        print("{startID}\t{endID}\t{file}".format(startID=args.startID,
                                                  endID=int.from_bytes(docID, 'big', signed=True),
                                                  file=filepath),
              file=docIDwetFile, flush=True)
        
                            
if args.docIDwet:
    docIDwetFile.close()
