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
