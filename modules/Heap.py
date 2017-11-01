import heapq
class FixSizeMaxHeap:
    def __init__(self, size: int):
        self.size = size
        self.data = []
        
    def push(self, item):
        if len(self.data) >= self.size:
            if item > self.data[0]:
                heapq.heapreplace(self.data, item)
        else:
            heapq.heappush(self.data,item)
        
    def pop(self):
        return heapq.heappop(self.data)

    def nlargest(self, n: int):
        return heapq.nlargest(n, self.data)

class FixSizeCountedMaxHeap(FixSizeMaxHeap):
    def __init__(self, size: int):
        super().__init__(size)
        self.length_original = 0

    def push(self, item):
        self.length_original += 1
        return super().push(item)
        
    def pop(self):
        self.length_original -= 1
        return super().pop()
        
class FixSizeMaxHeapSet(FixSizeMaxHeap):
    def push(self, item):
        if item not in self.data:
            return super().push(item)
