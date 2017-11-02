from modules import LexReader, Heap, BlockReader, Snippet

import pymongo

import time, functools

import configparser
Config = configparser.ConfigParser()
Config.read('config.ini')

import redis
r = redis.Redis(unix_socket_path=Config['Query']['RedisPath'], db=int(Config['Query']['RedisDB']))

import heapq

from langid.langid import LanguageIdentifier, model
possible_langs = ['zh', 'en','fr','de','it','la','es']
Language = LanguageIdentifier.from_modelstring(model, norm_probs=True)
Language.set_languages(possible_langs)
import jieba
jieba.initialize()

ii_file = open(Config['InvertedIndex']['IIFile'], mode='rb')

client = pymongo.MongoClient(Config['InvertedIndex']['MongoSock'])
termDB = client[Config['InvertedIndex']['TermDB']]
termIndexCollection : pymongo.collection.Collection = termDB.terms


def read_index():
    index_of_wet_path = Config['Query']['DocIDWet']
    LexReader.open_index(index_of_wet_path)
    return LexReader.index
read_index()

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

@functools.lru_cache(maxsize=65536)
def get_doc_abstract(docID: int):
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

@functools.lru_cache(maxsize=10240)
def get_term_abstract(term: str):
    """
    **cache**: Yes
    **returns**:
    ``` json
        {
            '_id': ObjectId('...'), 
            'term': b'\xe4\xb8\xad\xe6\x96\x87', 
            'count': 79848, 
            'off': 17839026787, 
            'begins': [...],
            'idOffs': [...],
            'tfOffs': [...],
            'bmOffs': [...]
        }
    ```
    """
    return termIndexCollection.find_one({'term': term.encode()})

def calculate_doc_summery(IDFs: [int], scoreTFs: [], docID: int):
    """
    **returns** (BM2.5_sumed, doc_abstract)
    """
    # both in order of terms
    # [IDF, ...]
    # [(extimated_score, TF), ... ] = scoreTFs 
    (offset, url, language, doc_length) = get_doc_abstract(docID)
    K = K_BM25(doc_length)
    return (
            sum([BM25(TF, K, IDF) 
                for (IDF, (_, TF)) 
                in zip(IDFs, scoreTFs)
                ]), 
            sum([TF for (_, TF) in scoreTFs]),
            docID,
            (offset, url, language, doc_length)
            )

def BM25_estimate(IDFs: [int], scoreTFs: [int]):
    return sum([idf*score for (idf, (score, tf)) in zip(IDFs, scoreTFs)])


def conjunctive_query(terms: [str], strict = False) -> (int, []):
    term_abstracts = [get_term_abstract(term) for term in terms]
    if strict:
        for term_table_result in term_abstracts:
            if term_table_result is None:
                return (0, [])
    else:
        (term_abstracts, terms) = zip(*[(term_abstract_result, term) for (term_abstract_result, term) in zip(term_abstracts, terms) if term_abstract_result is not None])
        if len(term_abstracts) == 0:
            return (0, [])
    
    term_abstracts = sorted(term_abstracts, key=lambda r: r['count'])
    IDFs = [IDF(term_len) for term_len in [r['count'] for r in term_abstracts]]
    
    conjReader = BlockReader.ConjunctiveBlockReader(ii_file, term_abstracts)
    
    # Stream fetch top 20 doc results
    conjunctiveScoreIDsTop20 = Heap.FixSizeCountedMaxHeap(20)
    [conjunctiveScoreIDsTop20.push((BM25_estimate(IDFs, scoreTFs), (scoreTFs, docID))) for (scoreTFs, docID) in conjReader]

    # Actual doc abstract fetch and cal
    doc_summeries = [calculate_doc_summery(IDFs, scoreTFs, docID) for (bm25_est, (scoreTFs, docID)) in  conjunctiveScoreIDsTop20.nlargest(10)]

    docs = [get_doc(docID, offset, url)
                    for (bm25, occurance, docID, (offset, url, language, doc_length) )
                    in doc_summeries]
                    
    return_items = [
        (url, language, title, bm25, occurance, 
        Snippet.generate(content, terms, lang=language)
        )
        for (
            (bm25, occurance, docID, (offset, url, language, doc_length)),
            (title, content)
        )
        in zip(doc_summeries, docs)
    ]
    return (conjunctiveScoreIDsTop20.length_original, return_items)

def single_query(term: str) -> (int, []):
    result = get_term_abstract(term)
    if result:
        block_reader = BlockReader.SimpleBlockReader(fileObj=ii_file,
                                   start_offset=result['off'], 
                                   begin_ids=result['begins'], 
                                   offsets_id=result['idOffs'], 
                                   offsets_tf=result['tfOffs'],
                                   offsets_score=result['bmOffs'])
        block_reader.read_first()
        
        conjunctiveScoreIDsTop20 = Heap.FixSizeCountedMaxHeap(20)
        [conjunctiveScoreIDsTop20.push(item) for item in block_reader]
        total_results = conjunctiveScoreIDsTop20.length_original

        result = [(docID, freq, get_doc_abstract(docID)) for (score, freq, docID) in conjunctiveScoreIDsTop20.nlargest(20)]

        idf = IDF(total_results)
        result = [(BM25(freq, K_BM25(doc_length), idf), docID, freq, offset, url, language) 
                  for (docID, freq, (offset, url, language, doc_length)) in  result]

        heapq.heapify(result)
        return_items = heapq.nlargest(10, result)

        return_items = [(
            get_doc(docID, offset, url), 
            (bm25, docID, freq, url, language)
            ) for (bm25, docID, freq, offset, url, language) in return_items]

        return (total_results, [(url, language, title, bm25, freq, Snippet.generate(content, [term], lang=language)) 
            for ((title, content),
                (bm25, docID, freq, url, language)) in return_items])
    else:
        return (0, [])

import re
latin_sep_words = re.compile(r"\W+")
non_latin_words_pattern = re.compile(r"([^\u0000-\u007F]|\w)+")

@functools.lru_cache(maxsize=512)
def query_exec(term: str):
    (term_lang, _) = Language.classify(term)
    if term_lang == 'zh':
        words = jieba.lcut(term)
        words = [word for word in words if non_latin_words_pattern.match(word)]
    else:
        words = latin_sep_words.split(term)
    print(term_lang, words)
    if len(words) > 1:
        (total_results, search_result) = conjunctive_query(words)
    else:
        # (total_results, search_result) = conjunctive_query(words)
        (total_results, search_result) = single_query(term)
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
    importlib.reload(BlockReader)
    importlib.reload(LexReader)
    importlib.reload(Snippet)
    importlib.reload(Heap)

def cache_info():
    return [("Query: ", str(query_exec.cache_info() )),
            ("Terms: ", str(get_term_abstract.cache_info() )),
            ("Docs : ", str(get_doc_abstract.cache_info() ))]

def cache_clear():
    query_exec.cache_clear()
    get_term_abstract.cache_clear()
    get_doc_abstract.cache_clear()
    pass

def close():
    ii_file.close()