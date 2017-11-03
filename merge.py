import sys
from tqdm import tqdm
from modules.IndexBlock import BlockWriter
import pymongo

import configparser
from functools import lru_cache

Config = configparser.ConfigParser()
Config.read('config.ini')


file = open(Config['InvertedIndex']['IIFile'], mode='wb')

client = pymongo.MongoClient(Config['InvertedIndex']['MongoSock'])
termDB = client[Config['InvertedIndex']['TermDB']]
termIndexCollection = termDB.terms

BM_N_doc = 8521860
BM_N_term = 4151693235
BM_Doc_AVG_Len = BM_N_term/BM_N_doc
BM_K1 = 1.2
BM_b  = 0.75
BM_K2 = BM_K1 * (1 - BM_b)
BM_K3 = BM_K1 * BM_b / BM_Doc_AVG_Len
def partial_BM25(TF: int, doc_length: int) -> int:
    return int(TF/(TF + BM_K2 + BM_K3 * doc_length) * 16384)


class DBAgent:
    bufferedCount = 0
    buffered = []

    def write(self):
        buffered = self.buffered
        termIndexCollection.bulk_write([pymongo.InsertOne(d) for d in buffered])
        self.buffered = []
        self.bufferedCount = 0

    def insert(self, doc):
        self.bufferedCount += 1
        self.buffered.append(doc)
        if self.bufferedCount > 400:
            self.write()

dbAgent = DBAgent()

import redis
r = redis.Redis(unix_socket_path=Config['Query']['RedisPath'], db=int(Config['Query']['RedisDB']))

@lru_cache(maxsize=8521860)
def doc_length(docID: int) -> int:
    return int(r.hmget(docID, 'len')[0])

class TermAgent:
    words = 0
    terms = 0
    current_block_writer = BlockWriter(file)

    def start_word(self, word):
        self.words += 1
        self.current_block_writer = BlockWriter(file)
        self.current_block_writer.write(word)

    def meet_document(self, content):
        docID, freq = content.split(b' ', 1)
        docID = int.from_bytes(docID, 'big', signed=True)
        freq = int(freq)
        bm25 = partial_BM25(freq, doc_length(docID))
        self.current_block_writer.add(docID, freq, score=bm25)

    def finish_word(self,word):
        self.terms += self.current_block_writer.count
        self.current_block_writer.finish()
        dbAgent.insert({
            'term'  : word,
            'count' : self.current_block_writer.count,
            'off'   : self.current_block_writer.start_offset,
            'begins': self.current_block_writer.begin_ids,
            'idOffs': self.current_block_writer.offsets_id,
            'tfOffs': self.current_block_writer.offsets_tf,
            'bmOffs': self.current_block_writer.offsets_score
        })

import atexit   
def exit_handler():
    print(doc_length.cache_info())
atexit.register(exit_handler)

if __name__ == "__main__":
    current_word = None
    agent = TermAgent()
    if Config['InvertedIndex']['ExpectTerms']:
        with open(Config['InvertedIndex']['ExpectTerms']) as expect_terms_file:
            expect_terms = int(expect_terms_file.readline())
        buffer = tqdm(sys.stdin.buffer, unit='lines', total=expect_terms)
    else:
        buffer = tqdm(sys.stdin.buffer, unit='lines')
    for line in buffer:
        word, contents = line.split(b'\t', 1)

        if current_word == word:
            agent.meet_document(contents[:-1])
        else:
            if current_word:
                agent.finish_word(current_word)
            current_word = word
            agent.start_word(current_word)
            agent.meet_document(contents[:-1])
            
    agent.finish_word(current_word)
    if dbAgent.bufferedCount>0:
        dbAgent.write()

    with open(Config['InvertedIndex']['StatisticsFile'], mode='w') as statistics_file:
        statistics_file.write("{terms}\t{words}".format(terms=agent.terms, words=agent.words))
    print('terms:', agent.terms, file=sys.stderr)
    print('words:', agent.words, file=sys.stderr)

   

    print('* Creating Index...', file=sys.stderr)

    termIndexCollection.create_index([("term", pymongo.HASHED)])
    # termIndexCollection.create_index([("term", pymongo.ASCENDING)], collation=pymongo.collation.Collation(locale="en", caseLevel=True, strength=2))
    # termIndexCollection.create_index([('term', pymongo.TEXT)], name='text')
    
file.close()
