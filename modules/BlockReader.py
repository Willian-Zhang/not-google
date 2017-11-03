from . import IndexBlock


SimpleBlockReader = IndexBlock.BlockReader

class ConjunctiveBlockReader:
    def __init__(self, blockreaders: [SimpleBlockReader]):
        self.blockreaders : [SimpleBlockReader] = blockreaders
    
    def read(self):
        [blockreader.read_first() for blockreader in self.blockreaders]
        # force start reading
        did = 1
        while did:
            i = 0
            # print((i, did) , end='')
            while i < len(self.blockreaders):
                done = self.blockreaders[i].next_GEQ(did)
                i += 1
                # print(' ->', (i, done) , end='')
                if done != did:
                    # not match in the middle
                    did = done
                    break
                elif i == len(self.blockreaders):
                    # match for last one
                    result :[(int, int)] = [blockreader.get_payload() for blockreader in self.blockreaders]
                    docID = did
                    did += 1
                    yield (result, docID)
            # print('')

    def __iter__(self):
        return self.read()

class DisjunctiveBlockreader:
    pass

def SimpleBlockReaderFromResult(fileObj, term_abstract) -> SimpleBlockReader:
    return SimpleBlockReader(fileObj=fileObj,
                             start_offset=term_abstract['off'], 
                             begin_ids=term_abstract['begins'], 
                             offsets_id=term_abstract['idOffs'], 
                             offsets_tf=term_abstract['tfOffs'],
                             offsets_score=term_abstract['bmOffs'])
