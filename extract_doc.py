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
parser.add_argument('-s','--startID', metavar='<number>', type=int, default=0,
                    help='docID Assigment starting after ID')
parser.add_argument('--endID', metavar='<number>', type=int,
                    help='expected ending ID')

parser.add_argument('-r', '--redis', metavar='<path/to/redis.sock>', default='/tmp/redis.sock',
                    help='if set, will use redis server to store URL Table')
parser.add_argument('-db', '--redisDB', metavar='<dbID>', type=int, default=0,
                    help='The DB to use in redis server')
parser.add_argument('-w', '--docIDwet', metavar='<path/to/docIDwet.tsv>',
                    help='If set, direct docID to wet summery to file')

args = parser.parse_args()


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
                    elif lang == 'zh' :
                        words = jieba.cut(content, cut_all=False)
                        # words = list(words)
                        words = [word for word in words if non_latin_words_pattern.match(word)]
                    else:
                        # other languages
                        continue

                    # words = [ word for word in words if word not in global_escape_words]
                    docLength = len(words)

                    docID = docIdGenerator.next()
                    r.hmset(docID, {
                        'url' : URI,
                        'lang': lang,
                        'len' : docLength,
                        'off' : offset
                    })

        # After each file:
        print("{startID}\t{endID}\t{file}".format(startID=args.startID,
                                                  endID=docID,
                                                  file=filepath),
              file=docIDwetFile, flush=True)
        
                            
if args.docIDwet:
    docIDwetFile.close()
