import sys
from tqdm import tqdm
from modules.IndexBlock import BlockWriter
import pymongo

import configparser

Config = configparser.ConfigParser()
Config.read('config.ini')


file = open(Config['InvertedIndex']['IIFile'], mode='wb')

client = pymongo.MongoClient(Config['InvertedIndex']['MongoSock'])
termDB = client[Config['InvertedIndex']['TermDB']]
termIndexCollection = termDB.terms

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
        self.current_block_writer.add(int.from_bytes(docID, 'big', signed=True), int(freq))

    def finish_word(self,word):
        self.terms += self.current_block_writer.count
        self.current_block_writer.finish()
        dbAgent.insert({
            'term'  : word,
            'count' : self.current_block_writer.count,
            'off'   : self.current_block_writer.start_offset,
            'begins': self.current_block_writer.begin_ids,
            'idOffs': self.current_block_writer.offsets_id,
            'tfOffs': self.current_block_writer.offsets_tf
        })
        

if __name__ == "__main__":

    termIndexCollection.create_index([("term", pymongo.HASHED)])

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
    print('|d|avg:', agent.terms/agent.words, file=sys.stderr)

    print('* Creating Index...', file=sys.stderr)
    
file.close()
