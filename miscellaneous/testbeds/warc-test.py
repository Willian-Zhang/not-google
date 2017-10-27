import warc
import sys
from tqdm import tqdm

print("** Test 1")
print("*Pass 1")
offsets = []
with warc.open('data/wet/CC-MAIN-20170919112242-20170919132242-00000.warc.wet.gz', 'rb') as f:
    i = 0
    
    for record, offset, length in f.browse():
        if i > 3:
            break
        URI = record.url
        print(i,  offset, length, URI)
        if URI:
            offsets.append(offset)
            i+=1

print("seeks:", offsets)
print("*Pass 2")
with warc.open('data/wet/CC-MAIN-20170919112242-20170919132242-00000.warc.wet.gz', 'rb') as f:
    i = 2
    f.seek(offsets[i])
    for record, offset, length in f.browse():
        if i > 5:
            break
        URI = record.url
        print(i, offset, length, URI)
        i+=1


print("** Test 2")
print("*Pass 1")
import time
offsets = []
i=0
with warc.open('data/wet/CC-MAIN-20170919112242-20170919132242-00000.warc.wet.gz', 'rb') as f:
    start = time.process_time()
    offset_last, length_last, URI_last = None, None, None
    for record, offset, length in f.browse():
        URI = record.url
        (offset_last, length_last, URI_last) = offset, length, URI
        offsets.append(offset)
        i+=1
    end = time.process_time()
    print("time:", end-start)

print("*Pass 2")
with warc.open('data/wet-uncompressed/CC-MAIN-20170919112242-20170919132242-00000.warc.wet', 'rb') as f:
    start = time.process_time()
    f.seek(offsets[-1])
    for record, offset, length in f.browse():
        URI = record.url
        print(i,  offset, length, URI)
    end = time.process_time()
    print("time:", end-start)