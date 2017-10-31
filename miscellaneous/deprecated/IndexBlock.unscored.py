from . import vbcode

class BlockWriter:
    _dump_size = 2048
    count = 0

    def __init__(self, fileObj):
        self.fileObj = fileObj
        self.start_offset = fileObj.tell()
        self.last_offset = fileObj.tell()

        self.begin_ids = []
        self.offsets_id = []
        self.offsets_tf = []
        
        self.last_id = 0
        self.ids = []
        self.tfs = []
    
    def write(self, bytess):
        self.fileObj.write(bytess)
        self.fileObj.flush()
        last = self.last_offset
        self.last_offset = self.fileObj.tell()
        return (last, self.last_offset - last)

    def _save(self):
        if len(self.ids) > 0:
            begin_id = self.ids[0]
            self.begin_ids.append(begin_id)

            encoded = vbcode.encode(self.ids)
            start_length_pair = self.write(encoded)
            self.offsets_id.append(start_length_pair)

            encoded = vbcode.encode(self.tfs)
            start_length_pair = self.write(encoded)
            self.offsets_tf.append(start_length_pair)

        self.last_id = 0
        self.ids = []
        self.tfs = []

    def add(self, docID, freq):
        self.ids.append(docID-self.last_id)
        self.tfs.append(freq)
        self.last_id = docID
        self.count += 1
        if len(self.ids) >= self._dump_size:
            self._save()
    
    def finish(self):
        self._save()

class BlockReader:
    def __init__(self, fileObj, start_offset, begin_ids, offsets_id, offsets_tf):
        self.fileObj = fileObj
        self.start_offset = start_offset
        # self.count  = count

        self.begin_ids = begin_ids
        self.offsets_id = offsets_id
        self.offsets_tf = offsets_tf

        self.current_block_indice = 0

        self.current_id = -1
        self.ids = []
        self.current_in_block_indice = -1
        self.tfs = []
        self.current_tf_block_indice = None
    
    def read_first(self):
        self._read_current_block_ids()
        self.current_in_block_indice = -1
        self.current_id = 0

    def _read_current_block_ids(self):
        offset, length = self.offsets_id[self.current_block_indice]
        self.fileObj.seek(offset)
        bytess = self.fileObj.read(length)
        self.ids = vbcode.decode(bytess)
        self.current_in_block_indice = 0
        self.current_id = self.ids[0]
        return self.current_id

    def _increment_current_in_block_id(self):
        self.current_in_block_indice += 1
        self.current_id += self.ids[self.current_in_block_indice]

    def next_GEQ(self, docID = None):
        """
        if same docID provided, will not consider EQ!
        """
        if docID is None:
            if self.current_in_block_indice < (len(self.ids) - 1):
                self._increment_current_in_block_id()
                return self.current_id 
            else:
                self.current_in_block_indice = 0
                if self.current_block_indice < (len(self.offsets_id) - 1):
                    self.current_block_indice += 1

                    self._read_current_block_ids()
                    
                    return self.current_id 
                else:
                    return None
        else:
            # may in next block : exist next block
            while self.current_block_indice < (len(self.begin_ids) - 1) and self.begin_ids[self.current_block_indice+1] <= docID:
                # in or after next block

                self.current_block_indice += 1

                # not 0 because later will add 1
                self.current_in_block_indice = -1
            if self.current_in_block_indice == -1:
                # block switched
                self._read_current_block_ids()

            # check current block
            while self.current_in_block_indice < (len(self.ids) - 1):
                self._increment_current_in_block_id()
                # still id left
                if self.ids[self.current_in_block_indice] > docID:
                    return self.current_id 
            return None

    def get_freq(self):
        """
        get TF of last read docID
        """
        if self.current_tf_block_indice != self.current_block_indice:
            # If not read
            self.current_tf_block_indice = self.current_block_indice
            offset, length = self.offsets_tf[self.current_tf_block_indice]
            self.fileObj.seek(offset)
            bytess = self.fileObj.read(length)
            self.tfs = vbcode.decode(bytess)
        # self.tfs read
        return self.tfs[self.current_in_block_indice]

    def __iter__(self):
        while True:
            docID = self.next_GEQ()
            if docID:
                freq = self.get_freq()
                yield (freq, docID)
            else:
                break
