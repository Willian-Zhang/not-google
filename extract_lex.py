import warc
import sys, os
import re
from uuid import UUID
import argparse
import slugid
from collections import Counter
from tqdm import tqdm

# NLP
from langid.langid import LanguageIdentifier, model
Language = LanguageIdentifier.from_modelstring(model, norm_probs=True)



# Options
parser = argparse.ArgumentParser(description='Extract Lexicons from WETs')
parser.add_argument('files', metavar='<filepath>', nargs='+',
                    help='path to file')
parser.add_argument('-b','--binary', action='store_true',
                    help='output docID and freqauncy as binary form')
parser.add_argument('-s','--startID', metavar='<number>', type=int, default=0,
                    help='docID Assigment starting after ID')

parser.add_argument('--skipChinese', action='store_true',
                    help='if set, will not parse chinese words')

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

if not args.skipChinese:
    import jieba
    list(jieba.cut(""))


# constants
space_devided_langs = ['en','fr','de','it','la','es']
latin_sep_words = re.compile(r"\W+")
# deprecated use non_latin_words_pattern
# chinese_stop_words = ['，', '\n','。',',', '.' ,'？','|',']','！','（','）', ' ', '\t']
global_escape_words = [b'\x00']
non_latin_words_pattern = re.compile(r"([^\u0000-\u007F]|\w)+")

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
                (lang, langConfidence) = Language.classify(content)
                if lang in space_devided_langs:
                    words = latin_sep_words.split(str(content))
                elif lang == 'zh' and not args.skipChinese:
                    words = jieba.cut(content, cut_all=False)
                    words = [word for word in words if len(word)<100 and non_latin_words_pattern.match(word)]
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
                    [print("{word}\t{uuid} {count}".format(
                        word=word, uuid=uuid.decode('ascii'), count=count
                        ))
                     for (word, count) in words]
                else:
                    docID = docIdGenerator.next()
                    if args.urlTable:
                        print("{docID}\t{url}\t{lan}".format(docID=docID, url=URI, lan=lang)
                              , file=fileURLTable)
                        # fileURLTable.write("{docID}\t{url}\t{lan}".format(docID=docID, url=URI, lan=lang))
                    if args.binary:
                        docID = docID.to_bytes(docIDDigits, 'little', signed=True)
                    else:
                        docID = str(docID)
                    for (word, count) in words: 
                        sys.stdout.write(word)
                        sys.stdout.write('\t')
                        if args.binary:
                            sys.stdout.buffer.write(docID)
                            sys.stdout.write(' ')
                            sys.stdout.buffer.write(count.to_bytes(frequancyDigits,'little', signed=True))
                        else:
                            sys.stdout.write(docID)
                            sys.stdout.write(' ')
                            sys.stdout.write(str(count))
                        sys.stdout.write('\n')
                            
if args.urlTable:
    fileURLTable.close()
