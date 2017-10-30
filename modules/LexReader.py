import warc
import sys
index = []
wet_average_length = 29263

def open_index(name, compressed = False):
    global index, wet_average_length
    # load index
    import csv
    with open(name, 'r') as tsvfile:
        tsv = csv.reader(tsvfile, delimiter="\t")
        if compressed:
            index = [(int(row[0]), int(row[1]), row[2]) for row in tsv]
        else:
            index = [(int(row[0]), int(row[1]), row[2].rstrip('.gz')) for row in tsv]
    
    # for more accurate guess
    min = index[0][0]
    max = index[-1][1]
    wet_average_length = (max - min) / len(index)

    if len(index) == 0:
        raise FileExistsError(name)
    


def which_wet(docID: int) -> str:
    # guess which wet
    i = int(docID / wet_average_length)
    # lower <docID<= higher
    if i >= len(index):
        return index[-1][2]
    #print("guess:", i, file=sys.stderr)
    while index[i][0] >= docID:
        #print('-', file=sys.stderr)
        i -= 1
    while index[i][1] < docID:
        #print('+', file=sys.stderr)
        i += 1
    #print("actual:", i, file=sys.stderr)
    return index[i][2]

def get_full_doc(docID: int, offset: int, url: str) -> str:
    with warc.open(which_wet(docID), 'rb') as f: # type:warc.WARCFile
        f.seek(offset)
        record = f.read_record()
        if url == record.url:
            return record.payload.read()
        else:
            return None

def close():
    pass