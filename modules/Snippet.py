from . import Heap

import jieba
jieba.initialize()

import re
latin_sep_words = re.compile(r"\W+")

from itertools import chain

def generate(content: str, keywords: [str], sentence_budget = 3, word_budget = 14, lang='en'):
    lines = content.split(sep="\n")
    if lang == 'zh':
        lines = [jieba.lcut(l) for l in lines]
        merger = ''
    else:
        lines = [latin_sep_words.split(l) for l in lines]
        merger = ' '

    small_lines = [l for l in lines if len(l)<= word_budget]
    big_lines   = [l for l in lines if len(l)> word_budget]
    del lines
    line_heap = Heap.FixSizeMaxHeapSet(sentence_budget)
    
    for line in small_lines:
        count = sum([1 for keyword in keywords if keyword in line])
        line_heap.push((count, line)) # cannot use iter
    del small_lines

    half_len = int(word_budget / 2)
    for line in big_lines:
        # a chunk is a future possible line
        half_chunks = [list(half_chunk) for half_chunk in sliding_window(line, size=half_len, step=half_len, fillvalue="")]
        countAndHalfs = [(sum([1 for keyword in keywords if keyword in half_chunk]), half_chunk)
                        for half_chunk in half_chunks]
        
        [line_heap.push((countA+countB, hcA+hcB)) for ((countA, hcA), (countB, hcB)) in sliding_window(countAndHalfs, size=2, step=1, fillvalue=[])]
    del big_lines

    sentences = [merger.join(line) for (count, line) in line_heap.nlargest(sentence_budget)]

    return sentences

# credit:
# https://stackoverflow.com/questions/6822725/rolling-or-sliding-window-iterator-in-python
from collections import deque
from itertools import islice

def sliding_window(iterable, size=2, step=1, fillvalue=None):
    it = iter(iterable)
    q = deque(islice(it, size), maxlen=size)
    if not q:
        return  # empty iterable or size == 0
    q.extend(fillvalue for _ in range(size - len(q)))  # pad to size
    while True:
        yield iter(q)  # iter() to avoid accidental outside modifications
        try:
            q.append(next(it))
        except StopIteration: # Python 3.5 pep 479 support
            return
        q.extend(next(it, fillvalue) for _ in range(step - 1))