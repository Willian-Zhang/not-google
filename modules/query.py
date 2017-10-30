from modules import IndexBlock
from modules import LexReader
import pymongo


import configparser
Config = configparser.ConfigParser()
Config.read('config.ini')

import redis
r = redis.Redis(unix_socket_path=Config['Query']['RedisPath'], db=int(Config['Query']['RedisDB']))

import heapq

ii_file = open(Config['InvertedIndex']['IIFile'], mode='rb')

client = pymongo.MongoClient(Config['InvertedIndex']['MongoSock'])
termDB = client[Config['InvertedIndex']['TermDB']]
termIndexCollection : pymongo.collection.Collection = termDB.terms


def read_index():
    index_of_wet_path = Config['Query']['DocIDWet']
    print(index_of_wet_path)
    LexReader.open_index(index_of_wet_path)
    return LexReader.index
read_index()

def get_doc(docID: int) -> str:
    # r.hmget(docID, ['off', 'url', 'lang', 'len'])
    # [b'297110936', b'https://...', b'en', b'1926']
    # {b'off': b'297110936', b'url': b'https://...', b'lang': b'en', b'len': b'1926'} 
    urlSlot = r.hgetall(docID)
    # // TODO: remove
    try:
        doc = LexReader.get_full_doc(docID, int(urlSlot[b'off']), urlSlot[b'url'].decode())
    except KeyError as identifier:
        import sys
        print("*Key error:", docID, file=sys.stderr)
        return (None, None)
    
    (title, doc) = doc.decode().split(sep="\n", maxsplit=1)
    return (docID,
            urlSlot[b'url'].decode(),
            urlSlot[b'lang'].decode(),
            urlSlot[b'len'].decode(),
            title, doc)
def BM25():
    pass
    
def get_term_single(term: str):
    result = termIndexCollection.find_one({'term': term.encode()})
    if result:
        block_reader = IndexBlock.BlockReader(fileObj=ii_file,
                                   start_offset=result['off'], 
                                   begin_ids=result['begins'], 
                                   offsets_id=result['idOffs'], 
                                   offsets_tf=result['tfOffs'])
        block_reader.read_first()

        result = [a for a in block_reader]
        total_results = len(result)
        
        heapq.heapify(result)

        return_docIDs = heapq.nlargest(10, result)
        
        docs = [get_doc(docID) for (freq, docID) in return_docIDs]
        return (total_results, [(url, lang, title) for (docID, url, lang, len, title, doc) in docs])
    else:
        return (0, [])

import time
def query(term: str):
    start = time.process_time()
    (total_results, search_result) = get_term_single(term)
    end = time.process_time()
    return {
        "meta":{
            "results": total_results,
            "time"   : end - start
        },
        "results": [{
            "url": url,
            "lang": lang,
            "title": title
        } for (url, lang, title) in search_result]
    }

import importlib
def reload():
    importlib.reload(IndexBlock)
    importlib.reload(LexReader)

def close():
    ii_file.close()