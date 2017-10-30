from struct import pack, unpack

'''

VariableByte: class for encoding and decoding a list of numbers
encoding_number : encoding base function to encode a number to byte format
encoding        : encoding a list of bytes to a single byte format
decoding        : decode a byte format to a list of numbers  

'''


class VariableByte:

    @staticmethod
    def encoding_number(number):

        number_to_bytes = []
        while True:
            number_to_bytes.insert(0, number % 128)
            if number < 128:
                break
            number = number // 128
        number_to_bytes[-1] += 128

        # PACK: we have a list of bytes [0-255] for the number in input, so we will convert the list to bytes object
        return pack('%dB' % len(number_to_bytes), *number_to_bytes)

    @staticmethod
    def encoding(numbers):

        bytes_list = []
        for number in numbers:
            bytes_list.append(VariableByte.encoding_number(number))

        # JOIN: Concatenate content of bytes object list to get single bytes object, so we will use unpack one time
        return b"".join(bytes_list)

    @staticmethod
    def encoding_pl(posting_list):

        bytes_list = []
        tuples_list = posting_list.ordered_access()
        for numbers_tuple in tuples_list:
            bytes_list.append(VariableByte.encoding(numbers_tuple))

        # JOIN: Concatenate content of bytes object list to get single bytes object, so we will use unpack one time
        return b"".join(bytes_list)

    @staticmethod
    def encoding_pl_list(posting_list_list):

        bytes_list = []
        for posting_list in posting_list_list:
            bytes_list.append(VariableByte.encoding_pl(posting_list))

        # JOIN: Concatenate content of bytes object list to get single bytes object, so we will use unpack one time
        return b"".join(bytes_list)

    @staticmethod
    def decoding(bytes_object):

        number = 0
        numbers = []

        # UNPACK : From single bytes object to bytes list
        bytes_list = unpack('%dB' % len(bytes_object), bytes_object)

        for byte in bytes_list:
            if byte < 128:
                number = 128 * number + byte
            else:
                number = 128 * number + (byte - 128)
                numbers.append(number)
                number = 0
        return numbers

