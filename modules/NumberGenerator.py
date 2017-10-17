


tbyte = int.from_bytes(b'\t','little',signed=True)
nbyte = int.from_bytes(b'\n','little',signed=True)

class Number:
    def __init__(self, digits = 4, start = 0):
        self.digits = digits
        self.byte_orders = range(0, 8*digits, 8)
        self.i = start
    
    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        # TODO: better implrementation, support space
        move = [1 if x^tbyte == 0 or x^nbyte == 0 else 0 
                 for x in self.i.to_bytes(self.digits,'little', signed=True)]
        move = sum([should_move << move_power for (should_move, move_power) in zip(move, self.byte_orders)])
        self.i += move + 1
        return self.i - 1

