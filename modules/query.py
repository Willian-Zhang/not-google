from modules import IndexBlock
from modules import LexReader
import pymongo

import numpy as np

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


import time
last_time = 0
def time_eslapsed(note):
    global last_time
    print(note, f"{(time.process_time()-last_time):.5f}")
    last_time = time.process_time()
    
def get_doc_deprecated(docID: int):
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

def get_snippets(content, keywords):
    first_three = content.split(sep="\n", maxsplit=3)[:3]
    return [one[:75] for one in first_three]

def get_doc(docID: int, offset: int, url: str):
    """
    return (title, content)
    """
    doc_full_content = LexReader.get_full_doc(docID, offset, url)
    splitted = doc_full_content.decode().split(sep="\n", maxsplit=1)
    if len(splitted) == 2:
        return splitted
    else:
        return (splitted[0], "")

def get_doc_index(docID: int):
    """
    return (offset, url, language, doc_length)
    """
    # r.hmget(docID, ['off', 'url', 'lang', 'len'])
    # [b'297110936', b'https://...', b'en', b'1926']
    # {b'off': b'297110936', b'url': b'https://...', b'lang': b'en', b'len': b'1926'} 
    urlSlot = r.hgetall(docID)
    
    return (int(urlSlot[b'off']),
            urlSlot[b'url'].decode(),
            urlSlot[b'lang'].decode(),
            int(urlSlot[b'len'].decode()))
import threading

def get_doc_index_mutiple(docIDs: [int]):
    """
    return (offset, url, language, doc_length)
    """
    # r.hmget(docID, ['off', 'url', 'lang', 'len'])
    # [b'297110936', b'https://...', b'en', b'1926']
    # {b'off': b'297110936', b'url': b'https://...', b'lang': b'en', b'len': b'1926'} 

    # docID100s = slice(docIDs, 100)

    p = r.pipeline(transaction=False)
    
    [p.hgetall(docID) for docID in docIDs]
    for urlSlot in p.execute():
        yield (int(urlSlot[b'off']),
                urlSlot[b'url'].decode(),
                urlSlot[b'lang'].decode(),
                int(urlSlot[b'len'].decode()))

N_doc = 49387975
N_term = 4151693235
Doc_AVG_Len = N_term/N_doc

import math
def IDF(term_len: int) -> float:
    return math.log((N_doc - term_len + 0.5)/(term_len + 0.5))

def K_BM25(doc_len: int) -> float:
    #0.75 = b
    #0.25 = 1-b
    return 1.2 * (0.25 +  0.75 * doc_len / Doc_AVG_Len )

def BM25(TF: int, K: float, IDF: float) -> float:
    # 2.2 = k1+1
    return IDF * (2.2 * TF) / (K * TF)
    
def conjunctive_query(terms):
    results = [ (term, termIndexCollection.find_one({'term': term.encode()})) for term in terms]
    for (_, term_table_result) in results:
        if term_table_result is None:
            return (0, [])
    results = sorted(results, lambda r: r['count'])
    blockreaders = [IndexBlock.BlockReader(fileObj=ii_file,
                                   start_offset=result['off'], 
                                   begin_ids=result['begins'], 
                                   offsets_id=result['idOffs'], 
                                   offsets_tf=result['tfOffs'])
                    for result in results]
    # blockreaders[0].read_first()
    for blockreader in blockreaders: 
        blockreader.read_first()

    conjunctiveIDs = []
    i = 0
    did = True
    while did:
        i = 0
        did = blockreaders[i].next_GEQ()
        while i < len(blockreaders):
            i += 1
            if blockreaders[i].next_GEQ(did) != did:
                # not match in the middle
                break
            elif i == (len(blockreaders) - 1):
                # match for last one
                
                freqs = [blockreader.get_freq() for blockreader in blockreaders]
                print("*match:", freqs)
                conjunctiveIDs.append((did, freqs))
    


def get_term_single(term: str):
    result = termIndexCollection.find_one({'term': term.encode()})
    if result:
        time_eslapsed("0 done")

        
        block_reader = IndexBlock.BlockReader(fileObj=ii_file,
                                   start_offset=result['off'], 
                                   begin_ids=result['begins'], 
                                   offsets_id=result['idOffs'], 
                                   offsets_tf=result['tfOffs'])
        block_reader.read_first()
        time_eslapsed("1 done")
        
        
        result = [a for a in block_reader]
        total_results = len(result)
        time_eslapsed("2 done")

        doc_abstracts = [*get_doc_index_mutiple([docID for (freq, docID) in  result])]
        time_eslapsed("3 done")

        idf = IDF(total_results)
        time_eslapsed("4.1 done")
        doc_lengths   = np.array([doc_length for (offset, url, language, doc_length) in doc_abstracts])
        time_eslapsed("4.2 done")
        freqs         = np.array([freq for (freq, docID) in  result])
        time_eslapsed("4.3 done")
        bm25s         = BM25(freqs, K_BM25(doc_lengths), idf)
        time_eslapsed("4.4 done")
        result = [(bm25, docID, freq, offset, url, language) 
                  for (bm25, (freq, docID), (offset, url, language, doc_length)) in  zip(bm25s, result, doc_abstracts)]
        time_eslapsed("4.5 done")

        heapq.heapify(result)
        time_eslapsed("5 done")
        return_items = heapq.nlargest(10, result)
        time_eslapsed("6 done")

        return_items = [(
            get_doc(docID, offset, url), 
            (bm25, docID, freq, url, language)
            ) for (bm25, docID, freq, offset, url, language) in return_items]

        time_eslapsed("7 done")
        return (total_results, [(url, language, title, bm25, freq, get_snippets(content, [term])) 
            for ((title, content),
                (bm25, docID, freq, url, language)) in return_items])
    else:
        return (0, [])



def query(term: str):
    start = time.process_time()
    (total_results, search_result) = get_term_single(term)
    end = time.process_time()
    return {
        "meta":{
            "results": total_results,
            "time"   : end - start,
            "query"  : term
        },
        "results": [{
            "url": url,
            "lang": lang,
            "title": title,
            "bm25": bm25,
            "count": freq,
            "snippets": snippets
        } for (url, lang, title, bm25, freq, snippets) in search_result]
    }

import importlib
def reload():
    importlib.reload(IndexBlock)
    importlib.reload(LexReader)

def close():
    ii_file.close()