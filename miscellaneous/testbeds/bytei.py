# Failed because piepline doesnot work
import uuid, sys

print(len(sys.argv))
input = sys.argv[1]
u = uuid.UUID(input)
print(u)
