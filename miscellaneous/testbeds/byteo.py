import uuid, sys
u = uuid.UUID("b8d73253d668449c9564a20392db65c4")
sys.stdout.buffer.write(u.bytes)
