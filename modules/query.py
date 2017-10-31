from modules import IndexBlock
from modules import LexReader
import pymongo

import time, functools

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
    LexReader.open_index(index_of_wet_path)
    return LexReader.index
read_index()

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

import math
BM_N_doc = 8521860
BM_N_term = 4151693235
BM_Doc_AVG_Len = BM_N_term/BM_N_doc
BM_K1 = 1.2
BM_K1_P1 = BM_K1 + 1
BM_b  = 0.75
BM_K2 = BM_K1 * (1 - BM_b)
BM_K3 = BM_K1 * BM_b / BM_Doc_AVG_Len
def IDF(term_len: int) -> float:
    return math.log((BM_N_doc - term_len + 0.5)/(term_len + 0.5))

def K_BM25(doc_len: int) -> float:
    # K = K2 + |d| * K3
    return BM_K2 + doc_len * BM_K3

def BM25(TF: int, K: float, IDF: float) -> float:
    # IDF * (K1 + 1) * TF / ( K + TF )
    return IDF * BM_K1_P1 * TF / (K * TF)
    
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
                                   offsets_tf=result['tfOffs'],
                                   offsets_score=result['bmOffs'])
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
        block_reader = IndexBlock.BlockReader(fileObj=ii_file,
                                   start_offset=result['off'], 
                                   begin_ids=result['begins'], 
                                   offsets_id=result['idOffs'], 
                                   offsets_tf=result['tfOffs'],
                                   offsets_score=result['bmOffs'])
        block_reader.read_first()

        result = [a for a in block_reader]
        total_results = len(result)
        
        heapq.heapify(result)
        result = heapq.nlargest(20, result)

        result = [(docID, freq, get_doc_index(docID)) for (score, freq, docID) in  result]

        idf = IDF(total_results)
        result = [(BM25(freq, K_BM25(doc_length), idf), docID, freq, offset, url, language) 
                  for (docID, freq, (offset, url, language, doc_length)) in  result]

        heapq.heapify(result)
        return_items = heapq.nlargest(10, result)

        return_items = [(
            get_doc(docID, offset, url), 
            (bm25, docID, freq, url, language)
            ) for (bm25, docID, freq, offset, url, language) in return_items]

        return (total_results, [(url, language, title, bm25, freq, get_snippets(content, [term])) 
            for ((title, content),
                (bm25, docID, freq, url, language)) in return_items])
    else:
        return (0, [])

@functools.lru_cache(maxsize=512)
def query_exec(term: str):
    (total_results, search_result) = get_term_single(term)
    return (total_results, search_result)

def query(term: str):
    start = time.process_time()
    (total_results, search_result) = query_exec(term)
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

def cache_info():
    return [("Query: ", str(query_exec.cache_info()))]

def cache_clear():
    query_exec.cache_clear()
    pass

def close():
    ii_file.close()