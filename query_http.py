from aiohttp import web
import socketio
from modules import query
import importlib

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)

async def index(request):
    """Serve the client-side application."""
    with open('index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')

# @sio.on('connect', namespace='/search')
# def connect(sid, environ):
#     print("connect ", sid)

@sio.on('search', namespace='/search')
async def search(sid, data: str):
    if data.startswith(':'):
        # commnad
        print(str(data))
        if data == ":reload":
            query.reload()
            importlib.reload(query)
            print("..reloaded")
            await sio.emit('simple info', data='Reloaded', room=sid, namespace='/search')
        elif data == ":cache":
            infos = query.cache_info()
            await sio.emit('multiple info', data=infos, room=sid, namespace='/search')
        elif data == ":cache-clear":
            query.cache_clear()
            await sio.emit('simple info', data='Cache Cleared', room=sid, namespace='/search')
    else:
        print("*search:", str(data))
        results = query.query(data)
        await sio.emit('search result', data=results, room=sid, namespace='/search')

# @sio.on('disconnect', namespace='/search')
# def disconnect(sid):
#     print('disconnect ', sid)

app.router.add_static('/static', 'static', append_version=True)
app.router.add_get('/', index)
app.router.add_get('/{any}', index)

if __name__ == '__main__':
    web.run_app(app)