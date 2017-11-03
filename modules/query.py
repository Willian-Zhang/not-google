from modules import LexReader, Heap, BlockReader, Snippet, BM25

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
    K = BM25.K_BM25(doc_length)
    return (
            sum([BM25.BM25(TF, K, IDF) 
                for (IDF, (_, TF)) 
                in zip(IDFs, scoreTFs)
                ]), 
            sum([TF for (_, TF) in scoreTFs]),
            docID,
            (offset, url, language, doc_length)
            )

def BM25_estimate(IDFs: [int], scoreTFs: [int]):
    return sum([idf*score for (idf, (score, tf)) in zip(IDFs, scoreTFs)])

@functools.lru_cache(maxsize=512)
def disjunctive_or_conjunctive_query(terms: [str], upper_threshold = 0.03, lower_threshold = 200, offset=0, length=10) -> (int, []):
    term_abstracts = [get_term_abstract(term) for term in terms]
    (term_abstracts, terms) = zip(*[(term_abstract_result, term) for (term_abstract_result, term) in zip(term_abstracts, terms) if term_abstract_result is not None])
    counts = [term_abs['count'] for term_abs in term_abstracts]
    total_count = sum(counts)
    min_count = min(counts)
    if total_count > upper_threshold * BM25.BM_N_doc and min_count > lower_threshold:
        print("Λ", end=' ')
        return conjunctive_query(terms, strict = False, offset=offset, length=length)
    else:
        print("|", end=' ')
        return disjunctive_query(terms, offset=offset, length=length)

@functools.lru_cache(maxsize=512)
def disjunctive_query(terms: [str], offset=0, length=10) -> (int, []):
    term_abstracts = [get_term_abstract(term) for term in terms]
    term_abstracts_and_term = [*zip(*[(term_abstract_result, term) for (term_abstract_result, term) in zip(term_abstracts, terms) if term_abstract_result is not None])]
    if term_abstracts_and_term:
        (term_abstracts, terms) = term_abstracts_and_term 
    else:
        return (0, [])
    if len(term_abstracts) == 0:
        return (0, [])
    
    IDFs = [BM25.IDF(term_len) for term_len in [r['count'] for r in term_abstracts]]

    reader = BlockReader.DisjunctiveBlockreader([BlockReader.SimpleBlockReaderFromResult(ii_file, term_abstract) for term_abstract in term_abstracts])

    # Stream fetch top 20 doc results
    scoreIDsTopDoubleOffseted = Heap.FixSizeCountedMaxHeap(offset+length*2)
    [scoreIDsTopDoubleOffseted.push((BM25_estimate(IDFs, scoreTFs), (scoreTFs, docID))) for (scoreTFs, docID) in reader]

    scoreIDsTopDoubleCut = Heap.FixSizeCountedMaxHeap(length*2)
    [scoreIDsTopDoubleCut.push(s) for s in scoreIDsTopDoubleOffseted.nsmallest(length*2)]

    doc_summeries = [calculate_doc_summery(IDFs, scoreTFs, docID) for (bm25_est, (scoreTFs, docID)) in  scoreIDsTopDoubleCut.nlargest(length)]

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
    return (scoreIDsTopDoubleOffseted.length_original, return_items)

@functools.lru_cache(maxsize=512)
def conjunctive_query(terms: [str], strict = False, offset=0, length=10) -> (int, []):
    """
    **strict**: 
    if True, return no result if there is no conjection
    else will ignore that term
    """
    term_abstracts = [get_term_abstract(term) for term in terms]
    if strict:
        for term_table_result in term_abstracts:
            if term_table_result is None:
                return (0, [])
    else:
        term_abstracts_and_term = [*zip(*[(term_abstract_result, term) for (term_abstract_result, term) in zip(term_abstracts, terms) if term_abstract_result is not None])]
        if term_abstracts_and_term:
            (term_abstracts, terms) = term_abstracts_and_term 
        else:
            return (0, [])
        if len(term_abstracts) == 0:
            return (0, [])
    
    term_abstracts = sorted(term_abstracts, key=lambda r: r['count'])
    IDFs = [BM25.IDF(term_len) for term_len in [r['count'] for r in term_abstracts]]
    
    reader = BlockReader.ConjunctiveBlockReader([BlockReader.SimpleBlockReaderFromResult(ii_file, term_abstract) for term_abstract in term_abstracts])
    
    # Stream fetch top 20 doc results
    scoreIDsTopDoubleOffseted = Heap.FixSizeCountedMaxHeap(offset+length*2)
    [scoreIDsTopDoubleOffseted.push((BM25_estimate(IDFs, scoreTFs), (scoreTFs, docID))) for (scoreTFs, docID) in reader]

    scoreIDsTopDoubleCut = Heap.FixSizeCountedMaxHeap(length*2)
    [scoreIDsTopDoubleCut.push(s) for s in scoreIDsTopDoubleOffseted.nsmallest(length*2)]

    doc_summeries = [calculate_doc_summery(IDFs, scoreTFs, docID) for (bm25_est, (scoreTFs, docID)) in  scoreIDsTopDoubleCut.nlargest(length)]

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
    return (scoreIDsTopDoubleOffseted.length_original, return_items)

@functools.lru_cache(maxsize=512)
def single_query(term: str, offset=0, length=10) -> (int, []):
    result = get_term_abstract(term)
    if result:
        block_reader = BlockReader.SimpleBlockReader(fileObj=ii_file,
                                   start_offset=result['off'], 
                                   begin_ids=result['begins'], 
                                   offsets_id=result['idOffs'], 
                                   offsets_tf=result['tfOffs'],
                                   offsets_score=result['bmOffs'])
        block_reader.read_first()
        
        scoreIDsTopDoubleOffseted = Heap.FixSizeCountedMaxHeap(offset+length*2)
        [scoreIDsTopDoubleOffseted.push(item) for item in block_reader]
        total_results = scoreIDsTopDoubleOffseted.length_original

        scoreIDsTopDoubleCut = Heap.FixSizeCountedMaxHeap(length*2)
        [scoreIDsTopDoubleCut.push(s) for s in scoreIDsTopDoubleOffseted.nsmallest(length*2)]

        result = [(docID, freq, get_doc_abstract(docID)) for (score, freq, docID) in scoreIDsTopDoubleCut.nlargest(length)]

        idf = BM25.IDF(total_results)
        result = [(BM25.BM25(freq, BM25.K_BM25(doc_length), idf), docID, freq, offset, url, language) 
                  for (docID, freq, (offset, url, language, doc_length)) in  result]

        heapq.heapify(result)
        return_items = heapq.nlargest(length, result)

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

import math

def query_exec(term: str, page):
    length = 10
    offset = length * page
    words = term.split('|')
    if len(words) == 1:
        (term_lang, _) = Language.classify(term)
        if term_lang == 'zh':
            words = jieba.lcut(term)
            words = [word for word in words if non_latin_words_pattern.match(word)]
        else:
            words = latin_sep_words.split(term)
        words = sorted(words)
        
        if len(words) > 1:
            (total_results, search_result) = disjunctive_or_conjunctive_query(frozenset(words), offset=offset, length=length)
        else:
            # (total_results, search_result) = disjunctive_query(frozenset(words), offset=offset, length=length)
            (total_results, search_result) = single_query(term, offset=offset, length=length)
        print(term_lang, words)
    else:
        words = sorted(words)
        
        (total_results, search_result) = disjunctive_query(frozenset(words), offset=offset, length=length)
        print(words)
    pages = math.ceil(total_results/length)
    meta = (total_results, words, pages, page)
    return (meta, search_result)

def query(term: str, page=0):
    start = time.process_time()
    (meta, search_result) = query_exec(term, page)
    (total_results, keywords, pages, page) = meta
    end = time.process_time()
    return {
        "meta":{
            "results": total_results,
            "time"   : end - start,
            "query"  : term,
            "keywords": keywords,
            "pages"   : pages,
            "page"    : page
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
    importlib.reload(BM25)

def cache_info():
    return [("Single Query: ", str(single_query.cache_info() )),
            ("Conjuctive Query: ", str(conjunctive_query.cache_info() )),
            ("Disjunctive Query: ", str(disjunctive_query.cache_info() )),
            ("Compand Query: ", str(disjunctive_or_conjunctive_query.cache_info() )),
            ("Terms: ", str(get_term_abstract.cache_info() )),
            ("Docs : ", str(get_doc_abstract.cache_info() ))] + BlockReader.cache_info()

def cache_clear():
    # query_exec.cache_clear()
    get_term_abstract.cache_clear()
    get_doc_abstract.cache_clear()
    disjunctive_or_conjunctive_query.cache_clear()
    conjunctive_query.cache_clear()
    disjunctive_query.cache_clear()
    single_query.cache_clear()
    BlockReader.clear_cache()
    pass

def close():
    ii_file.close()