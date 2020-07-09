from app import app, jinja
from sanic import response
import pydest
import json
from jinja2 import Environment, PackageLoader, select_autoescape


# template_env = Environment(
#     loader=PackageLoader('templates'),
#     autoescape=select_autoescape(['html', 'xml']),
#     enable_async=True
# )


@app.route('/')
@app.route('/eververse')
@jinja.template('ev.html')
async def eververse(request):
    # template = template_env.get_template("ev.html")
    # rendered_template = await template.render_async(
    #     knights='that say nih; asynchronously')
    # return response.html(rendered_template)
    # return await response.file('static/ev.html')
    return {}


@app.route('/daily')
async def daily(request):
    return await response.file('static/daily.html')


@app.route('/weekly')
async def weekly(request):
    return response.html('<!DOCTYPE html lang="ru">\n'
                         '<html lang="ru">\n'
                         '<meta name="theme-color" content="#222222">\n'
                         '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                         '<link rel="stylesheet" type="text/css" href="/static/style.css">\n'
                         '<header class="header-fixed">\n'
                         '    <div class="header-limiter">\n'
                         '		<h1><a href="/">d2info</a></h1>\n'
                         '		<nav>\n'
                         '			<a href="/">Главная</a>\n'
                         '            <a href="/daily">Сегодня</a>\n'
                         '            <a href="/weekly">На этой неделе</a>\n'
                         '			<a href="/eververse">Эверверс</a>\n'
                         '		</nav>\n'
                         '	</div>\n'
                         '</header>\n'
                         '<div class="header-fixed-placeholder"></div>\n'
                         '<title>{}</title>\n'
                         '<h2>Пока что данные не предоставляются</h2>'.format('На этой неделе'))


@app.route('/item')
async def item(request):
    api_data_file = open('api.json', 'r')
    api_data = json.loads(api_data_file.read())
    d2 = pydest.Pydest(api_data['key'])
    item_manifest = await d2.decode_hash(request.args['hash'][0], 'DestinyInventoryItemDefinition', language='ru')
    if 'screenshot' in item_manifest.keys():
        screenshot = '<img class="screenshot" src="https://bungie.net{}">'.format(item_manifest['screenshot'])
    else:
        screenshot = '<img class="icon" src="https://bungie.net{}">'.format(item_manifest['displayProperties']['icon'])
    await d2.close()
    return response.html('<!DOCTYPE html lang="ru">\n'
                         '<html lang="ru">\n'
                         '<meta name="theme-color" content="#222222">\n'
                         '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                         '<link rel="stylesheet" type="text/css" href="/static/style.css">\n'
                         '<header class="header-fixed">\n'
                         '    <div class="header-limiter">\n'
                         '		<h1><a href="/">d2info</a></h1>\n'
                         '		<nav>\n'
                         '			<a href="/">Главная</a>\n'
                         '            <a href="/daily">Сегодня</a>\n'
                         '            <a href="/weekly">На этой неделе</a>\n'
                         '			<a href="/eververse">Эверверс</a>\n'
                         '		</nav>\n'
                         '	</div>\n'
                         '</header>\n'
                         '<div class="header-fixed-placeholder"></div>\n'
                         '<title>{}</title>\n'
                         '<link rel="icon" type="image/png" sizes="32x32" href="https://bungie.net{}">\n'
                         '{}\n'
                         '<h3>{}</h3>\n'
                         '<a>{}</a><br>\n'
                         '<form method="get" action="/eververse">\n'
                         '    <button type="submit">Вернуться назад</button>\n'
                         '</form>\n'
                         .format(item_manifest['displayProperties']['name'], item_manifest['displayProperties']['icon'],
                                 screenshot, item_manifest['displayProperties']['name'], item_manifest['displayProperties']['description']))
