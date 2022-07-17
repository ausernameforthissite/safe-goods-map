from aiohttp import web
import aiohttp
import aiohttp_cors
from dsworker import DSWorker
import yaml

cache = dict()

with open("./config.yaml", 'r') as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

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

dsworker = DSWorker(config['datascienceinfo'])

if __name__ == "__main__":
    web.run_app(app, host=config['host'], port=config['port'])
