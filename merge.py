import sys
from tqdm import tqdm

current_word = None
#current_count = 0

for line in tqdm(sys.stdin.buffer, unit='lines'):
    word, contents = line.split(b'\t', 1)

    if current_word == word:
        #current_count += 1
        sys.stdout.buffer.write(contents[:-1])
    else:
        if current_word:
            sys.stdout.buffer.write(b'\n')
            sys.stdout.buffer.flush()
        current_word = word
        #current_count = 1
        sys.stdout.buffer.write(current_word)
        
sys.stdout.buffer.write(b'\n')
sys.stdout.buffer.flush()