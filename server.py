from aiohttp import web
import aiohttp
import aiohttp_cors
from dsworker import DSWorker
import yaml
import codecs

cache = dict()

with open("./config.yaml", 'r') as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

def getFile(path):
    file = codecs.open(path, 'r', encoding='utf-8')
    file_str = file.read()
    file.close()
    return file_str

async def start(request):
    return web.Response(text=getFile('home.html'), content_type='text/html', status=200)
    
async def js(request):
    return web.Response(text=getFile('index.js'), status=200)

async def check(request):
    params = await request.json()
    response = dsworker.check(params)
    return web.json_response(response, status=200)

async def getInfo(request):
    params = await request.json()
    response = dsworker.getInfo(params)
    return web.json_response(response, status=200)

async def getAddresses(request):
    params = await request.json()
    response = dsworker.getAddresses(params)
    return web.json_response(response, status=200)

async def getCoordinates(request):
    params = await request.json()
    if params['url'] in cache:
        return web.json_response(cache[params['url']], status=200)
    async with aiohttp.ClientSession() as session:
        async with session.get(params['url']) as resp:
            cache[params['url']] = await resp.json()
            return web.json_response(cache[params['url']], status=200)

routes = [['/check', check], ['/getInfo', getInfo], ['/getAddresses', getAddresses], ['/getCoordinates', getCoordinates]]
routes_get = [['/start', start], ['/js', js]]

app = web.Application()
cors = aiohttp_cors.setup(app, defaults={
    "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
})

for route in routes:
    resource = cors.add(app.router.add_resource(route[0]))
    cors.add(resource.add_route('POST', route[1]))

for route in routes_get:
    resource = cors.add(app.router.add_resource(route[0]))
    cors.add(resource.add_route('GET', route[1]))

dsworker = DSWorker(config['datascienceinfo'])
#dsworker.task('?????? ??????????????_??????????.xlsx', '????????1', '????????2', 'output.xlsx')

if __name__ == "__main__":
    web.run_app(app, host=config['host'], port=config['port'])
