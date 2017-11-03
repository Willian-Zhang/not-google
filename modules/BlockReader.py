from . import IndexBlock, Heap

SimpleBlockReader = IndexBlock.BlockReader

class ConjunctiveBlockReader:
    def __init__(self, blockreaders: [SimpleBlockReader]):
        self.blockreaders : [SimpleBlockReader] = blockreaders
        self.did = 1
    
    def read(self):
        [blockreader.read_first() for blockreader in self.blockreaders]
        # force start reading
        did = 1
        while self.did:
            i = 0
            # print((i, self.did) , end='')
            while i < len(self.blockreaders):
                done = self.blockreaders[i].next_GEQ(self.did)
                i += 1
                # print(' ->', (i, done) , end='')
                if done != self.did:
                    # not match in the middle
                    self.did = done
                    break
                elif i == len(self.blockreaders):
                    # match for last one
                    result :[(int, int)] = [blockreader.get_payload() for blockreader in self.blockreaders]
                    yield (result, self.did)
                    self.did += 1
            # print('')

    def make_did(self, docID: int):
        self.did = docID

    def __iter__(self):
        return self.read()

Dummy_None_Payload = (0, 0) # 0 estimated score 0 freq
class DisjunctiveBlockreader:
    def __init__(self, blockreaders: [SimpleBlockReader]):
        self.blockreaders : [SimpleBlockReader] = blockreaders
        # heap of (id, blockreader_indice), fixsize of len(blockreaders)
        self.heap =  Heap.Heap() 
        self.did = None
    
    def read(self):
        [blockreader.read_first() for blockreader in self.blockreaders]
        for i in range(len(self.blockreaders)):
            id = self.blockreaders[i].next_id()
            if id:
                self.heap.push((id, i))

        while self.heap.data:
            readings = []
            while self.heap.data:
                (self.did, i) = self.heap.pop()
                blockreader = self.blockreaders[i]
                payload = blockreader.get_payload()
                # fetch one get one
                id = blockreader.next_id()
                if id:
                    self.heap.push((id, i))
                readings.append((i, payload))

                if not self.heap.data or self.heap.data[0][0] != self.did: # id changed
                    readings = sorted(readings)
                    yield ([readings.pop()[1] if readings and i == readings[0][0] else Dummy_None_Payload for i in range(len(self.blockreaders))], self.did)
                    break
                
    def make_did(self, docID: int):
        self.did = docID

    def __iter__(self):
        return self.read()

def SimpleBlockReaderFromResult(fileObj, term_abstract) -> SimpleBlockReader:
    return SimpleBlockReader(fileObj=fileObj,
                             start_offset=term_abstract['off'], 
                             begin_ids=term_abstract['begins'], 
                             offsets_id=term_abstract['idOffs'], 
                             offsets_tf=term_abstract['tfOffs'],
                             offsets_score=term_abstract['bmOffs'])

def cache_info():
    return [
        ("Blocks: ", str(IndexBlock.decode_file_part.cache_info() ))
    ]

def clear_cache():
    IndexBlock.decode_file_part.cache_clear()