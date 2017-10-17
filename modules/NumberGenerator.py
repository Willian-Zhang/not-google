


tbyte = int.from_bytes(b'\t','little',signed=True)
nbyte = int.from_bytes(b'\n','little',signed=True)
sbyte = int.from_bytes(b' ','little',signed=True)

class Number:
    """
    Get Numbers avoiding '\t' '\n' and <space>
    """
    def __init__(self, digits = 4, after = 0):
        self.digits = digits
        self.byte_orders = range(0, 8*digits, 8)
        self.i = after
    
    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def _get_move(self, number):
        move = [1 if b^tbyte == 0 or b^nbyte == 0 or b^sbyte == 0 else 0
                for b in number.to_bytes(self.digits, 'little', signed=True)]
        return sum([should_move << move_power
                    for (should_move, move_power) in zip(move, self.byte_orders)])

    def next(self):
        """
        Get next Number avoiding '\t' '\n' and <space>
        """
        move = 1
        while move > 0:
            self.i += move
            move = self._get_move(self.i)

        return self.i
