#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Implementation of Golomb-coded sets.

Invocable from the command-line as a crude spell-checker.

Golomb-coded sets are another probabilistic data structure similar in
nature to bloom filters.  In fact, you can think of them as a kind of
compressed bloom filter, using a single hash function.

They are more compact, slower, and more complex in implementation than
bloom filters.  This one uses 69204 bytes to encode the 98763 words
from my /usr/share/dict/words with a false-positive probability of
1/16, or 5.6 bits per item.  An uncompressed bloom filter needs about
71243 bytes to do the same thing: four hash functions means 98763 * 4
bits set, and ((71243*8-1)/(71243*8))**(98763*4) is just over 0.5, so
a four-hash bloom filter of this size is expected to reach 50% fill
factor at 98763 items.

But that’s only about 3% smaller.  The advantage gets bigger as the
false-positive probability gets higher.  For a false-positive
probability of 1/2**32, this uses 414652 bytes, or 33.6 bits per item.
In bc -l, 1/(1-e(l(1/2)/(98763*32)))/8 tells me a 32-function bloom
filter would need 569940 bytes, about 37% more.

Note that this is very close to the theoretical limit of Golomb-Rice
compression: 32 bits per item are used to code the remainder, and at
least one bit to encode the quotient, so there's only 0.6 bits per
item left over.  (Which was also true with the 5.6 bits per item.)
There probably aren’t any hash collisions in this set, so the lack of
code to eliminate them is not important.

(/usr/share/dict/words is 98569 lines.  The discrepancy in the number
of words comes from accented letters, which this program doesn’t
consider to be letters, and from capitalization, which this program
doesn’t consider significant.)

The 37% savings seems fairly minimal to me.  On the other hand, now I
have a Python implementation of Golomb-Rice coding, which should be
useful for one of my text search engines.

For more information:

<http://giovanni.bajo.it/2011/09/golomb-coded-sets/>  
<http://en.wikipedia.org/wiki/Golomb_coding>
<http://www.imperialviolet.org/2011/04/29/filters.html>

Remaining problems:

- incredibly, painfully slow (fixable with buckets)
- unpleasant API which requires a list of items up front.
- clumsy and overcomplicated merge algorithm
- tests are in funny places
- uses outrageous amounts of memory for set construction
- should say "Golomb-Rice" when it talks about the coding system it uses
- golomb_encode yields bits, but golomb_decode consumes bytes.

"""
import itertools, re

try:
    from hashlib import sha1 as sha
except ImportError:
    from sha import sha

def ok(a, b): assert a == b, (a, b)

def main(dictfilename, false_positive_bits, infilename):
    "Example command-line program using Golomb-coded sets for spell-checking."
    contents = list(words(open(dictfilename)))
    dictionary = make_gcs(contents, false_positive_bits)
    print(("Dictionary is %d bytes, %d words" % (len(dictionary[2]),
                                                len(contents))))

    misspellings = set()
    # We use len(contents) as the chunk size because that’s the
    # sweet spot for efficiency.
    for word_chunk in chunks(words(open(infilename)), len(contents)):
        for word, contained in gcs_test(dictionary, word_chunk):
            if not contained and word not in misspellings:
                misspellings.add(word)
                print(word)

def words(fileobj):
    "Iterator over all the English words in a file."
    for line in fileobj:
        for word in re.findall("[\w']+", line):
            yield word.lower()

def chunks(iterable, length):
    "Read from an iterator in chunks up to some maximum length."
    items = iter(iterable)
    while True:
        rv = []
        for ii in range(length):
            try:
                item = next(items)
            except StopIteration:
                yield rv
                return
            rv.append(item)
        yield rv

ok(list(chunks(list(range(10)), 3)),
   [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]])

def make_gcs(items, false_positive_bits):
    "Construct a Golomb-coded set from a list of items."
    expected_interval = 2**false_positive_bits
    hash_size = len(items) * expected_interval
    diffs = deltas(sorted(sha1_long(item) % hash_size
                          for item in items))

    bits = itertools.chain.from_iterable(
        golomb_encode(delta, false_positive_bits) for delta in diffs)

    bytes = pack_bits(bits)
    return (len(items), false_positive_bits, ''.join(bytes))

def gcs_contains(gcs, item):
    "Returns true if the Golomb-coded set contains the item."
    for _, contained in gcs_test(gcs, [item]):
        return contained

def gcs_test(gcs, items):
    """Test which of the items in the iterable are contained in the GCS.

    Yield (item, contained) for each item in items, but out of order.

    This takes time roughly proportional to the number of items that
    have ever been added to the GCS plus the number of items being
    tested.

    """
    count, false_positive_bits, bytes = gcs
    hash_size = count * 2**false_positive_bits
    needles = [(sha1_long(item) % hash_size, item) for item in items]
    needles.sort()
    needles = iter(needles)
    needle = next(needles)

    haystack = partial_sums(golomb_decode(bytes, false_positive_bits))
    try:
        hay = (next(haystack),)
    except StopIteration:
        hay = None

    while True:
        if hay is None or needle[0] < hay[0]:
            yield needle[1], False      # not contained
            needle = next(needles)
        elif needle[0] == hay[0]:
            yield needle[1], True       # contained, or false positive
            needle = next(needles)
        else:
            try:
                hay = (next(haystack),)
            except StopIteration:
                hay = None

def sha1_long(str):
    "Return the SHA-1 hash of a string as a large integer."
    return int(sha(str.encode()).hexdigest(), 16)

def golomb_encode(number, bits):
    "Yields a sequence of bits Golomb-coding the number with divisor 2**bits."
    qq, rr = divmod(number, 2**bits)

    for ii in range(qq):
        yield 1
    yield 0

    for ii in range(bits-1, -1, -1):    # most significant bit first
        yield 1 if rr & (1 << ii) else 0

# 2038 == 3 * 512 + 502
ok(list(golomb_encode(2038, 9)), [1, 1, 1, 0,  # three 512s
                                  1, 1, 1, 1, 1, 0, 1, 1, 0, # 502
                                  ])

def pack_bits(bits):
    """Yields a sequence of bytes containing the specified sequence of bits.

    Big-endian, and packs stray bits into the last byte left-justified
    with zeroes.

    """
    buf, bufptr = 0, 0

    for bit in bits:
        buf = buf << 1 | bit
        bufptr += 1

        if bufptr == 8:
            yield chr(buf)
            buf, bufptr = 0, 0

    if bufptr:
        yield chr(buf << (8 - bufptr))

ok(''.join(pack_bits([0, 0, 1, 0, 0, 1, 0, 0,
                      0, 0, 1, 0, 0, 1, 0, 1,
                      1, 0, 1])),
   '$%\xa0')

def deltas(items):
    """Inverse function of partial_sums."""
    last = 0
    for item in items:
        yield item - last
        last = item

ok(list(deltas([3, 5, 10, 100])), [3, 2, 5, 90])

def partial_sums(items):
    """Returns partial sums of the first N items in a list."""
    last = 0
    for item in items:
        last += item
        yield last

ok(list(partial_sums([3, 2, 5, 90])), [3, 5, 10, 100])

def golomb_decode(bytes, bits):
    """Yields each of the numbers Golomb-encoded in bytes with divisor 2**bits.

    Not quite the inverse of golomb_encode; that encodes only a single
    number, and encodes it as a sequence of bits.  Otherwise, though,
    the two are inverses.

    """
    bit_seq = unpack_bits(bytes)

    while True:              # or until bit_seq throws a StopIteration
        qq = 0
        while next(bit_seq) == 1:
            qq += 1

        rr = 0
        for ii in range(bits):
            rr = rr << 1 | next(bit_seq)

        yield qq << bits | rr

def unpack_bits(bytes):
    """Yields the bits in a sequence of bytes."""
    for byte in bytes:
        byte = ord(byte)
        for ii in range(7, -1, -1):     # 8 bits per byte
            yield 1 if byte & (1 << ii) else 0

ok(list(unpack_bits("$%\xa0")),
   [0, 0, 1, 0, 0, 1, 0, 0,
    0, 0, 1, 0, 0, 1, 0, 1,
    1, 0, 1, 0, 0, 0, 0, 0,
    ])

ok(list(golomb_decode(pack_bits([1, 1, 1, 0,
                                 1, 1, 1, 1, 1, 0, 1, 1, 0,
                                 0,
                                 0, 0, 0, 0, 0, 0, 0, 0, 1,
                                 ]), 9)),
   [2038, 1])
    
def _system_test():
    """Simple smoke-test function."""
    gcs = make_gcs(["the", "and", "of"], 16)
    present, absent = set(), set()
    for item, contained in gcs_test(gcs, ["the", "rnd", "dof", "of"]):
        if contained:
            present.add(item)
        else:
            absent.add(item)
    ok(present, set(["the", "of"]))
    ok(absent, set(["rnd", "dof"]))

_system_test()

if __name__ == '__main__':
    import sys
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3])