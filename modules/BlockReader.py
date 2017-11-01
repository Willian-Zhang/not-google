from . import IndexBlock

class ConjunctiveBlockReader:
    def __init__(self, fileObj, results: []):
        self.blockreaders : [IndexBlock.BlockReader] = [IndexBlock.BlockReader(fileObj=fileObj,
                                                                    start_offset=result['off'], 
                                                                    begin_ids=result['begins'], 
                                                                    offsets_id=result['idOffs'], 
                                                                    offsets_tf=result['tfOffs'],
                                                                    offsets_score=result['bmOffs'])
                                                        for result in results]
    
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

SimpleBlockReader = IndexBlock.BlockReader
