from modules import query
import cmd
import time
import importlib

class CommandLine(cmd.Cmd):
    
    def do_search(self, line: str):
        start = time.process_time()
        result = query.get_term_single(line)
        end = time.process_time()
        
        print(result)
        print("* time:", end - start)

    def do_reload(self, _):
        start = time.process_time()
        
        importlib.reload(query.IndexBlock)
        importlib.reload(query.LexReader)
        importlib.reload(query)

        end = time.process_time()
        print("* load time:", end - start)
    
    def do_wet(self, docID: str):
        docID = int(docID)
        start = time.process_time()
        
        if docID:
            result = query.LexReader.which_wet(docID)
        else:
            result = query.read_index()
        
        end = time.process_time()
        print(result)
        print("* load time:", end - start)
    
    def do_doc(self, docID: str):
        docID = int(docID)
        start = time.process_time()
        
        if docID:
            result = query.get_doc(docID)
        else:
            result = "Please provide docID(number)"
        
        end = time.process_time()
        print(result)
        print("* load time:", end - start)
        
    def do_EOF(self, line: str):
        print("")
        query.close()
        return True

if __name__ == '__main__':
    CommandLine().cmdloop()