from app import app, jinja
from sanic import response
import pydest
import json
import sqlite3
import mariadb
import markdown2


api_data_file = open('api.json', 'r')
api_data = json.loads(api_data_file.read())


@app.route('/')
@jinja.template('index.html')
async def index(request):
    return {}


@app.route('/eververse')
@jinja.template('ev.html')
async def eververse(request):
    data_db = sqlite3.connect('data.db')
    data_cursor = data_db.cursor()
    data_cursor.execute('''SELECT items FROM season_ev''')
    items = data_cursor.fetchone()
    if items is not None:
        items = eval(items[0])
    else:
        items = {
            'name': 'Нет данных. Проверьте позднее.',
            'items': []
        }
    data_db.close()
    return jinja.render('ev.html', request, global_items=items)


@app.route('/evweekly')
@jinja.template('evweekly.html')
async def ev_weekly(request):
    data_db = sqlite3.connect('data.db')
    data_cursor = data_db.cursor()
    data_cursor.execute('''SELECT items FROM evweekly''')
    items = data_cursor.fetchone()
    if items is not None:
        items = eval(items[0])
    else:
        items = [{
            'name': 'Нет данных, или они пока что не предоставляются. Проверьте позднее.',
            'items': []
        }]
    data_db.close()
    return jinja.render('evweekly.html', request, global_items=items, item_style='max-width: 400px', global_style='grid-template-columns: repeat(auto-fit, minmax(250px,1fr))')


@app.route('/v1/daily')
@jinja.template('daily.html')
async def daily(request):
    data_db = sqlite3.connect('data.db')
    data_cursor = data_db.cursor()
    data_cursor.execute('''SELECT items FROM dailyrotations''')
    items = data_cursor.fetchone()
    if items is not None:
        items = eval(items[0])
    else:
        items = {
            'name': 'Нет данных. Проверьте позднее.',
            'items': []
        }
    data_db.close()
    return jinja.render('daily.html', request, global_items=items)


@app.route('/daily')
@jinja.template('daily.html')
async def dyn_daily(request):
    data_db = mariadb.connect(host=api_data['db_host'], user=api_data['cache_login'],
                              password=api_data['pass'], port=api_data['db_port'],
                              database=api_data['data_db'])
    db_cursor = data_db.cursor()
    items = []
    db_cursor.execute('''SELECT json, name, size, template FROM ru WHERE type='daily' ORDER BY place ASC''')
    data = db_cursor.fetchall()
    for item in data:
        items.append({
            'name': item[1],
            'size': item[2],
            'items': json.loads(item[0])['data'],
            'template': item[3]
        })

    data_db.close()
    return jinja.render('daily.html', request, global_items=items)


@app.route('/weekly')
@jinja.template('weekly.html')
async def dyn_weekly(request):
    data_db = mariadb.connect(host=api_data['db_host'], user=api_data['cache_login'],
                              password=api_data['pass'], port=api_data['db_port'],
                              database=api_data['data_db'])
    db_cursor = data_db.cursor()
    items = []
    db_cursor.execute('''SELECT json, name, size, template FROM ru WHERE type='weekly' ORDER BY place ASC''')
    data = db_cursor.fetchall()
    for item in data:
        items.append({
            'name': item[1],
            'size': item[2],
            'items': json.loads(item[0])['data'],
            'template': item[3]
        })

    data_db.close()
    return jinja.render('weekly.html', request, global_items=items)


@app.route('/v1/weekly')
@jinja.template('weekly.html')
async def weekly(request):
    data_db = sqlite3.connect('data.db')
    data_cursor = data_db.cursor()
    data_cursor.execute('''SELECT items FROM weeklyrotations''')
    items = data_cursor.fetchone()
    if items is not None:
        items = eval(items[0])
    else:
        items = [{
            'name': 'Нет данных, или они пока что не предоставляются. Проверьте позднее.',
            'items': []
        }]
    data_db.close()
    return jinja.render('weekly.html', request, global_items=items)


@app.route('/api')
@jinja.template('api.html')
async def api(request):
    md = markdown2.markdown_path('app/templates/api.md')
    return jinja.render('api.html', request, md=md)


@app.route('/api/dailyrotations')
async def dailyrotations(request):
    data_db = sqlite3.connect('data.db')
    data_cursor = data_db.cursor()
    data_cursor.execute('''SELECT items FROM dailyrotations''')
    items = data_cursor.fetchone()
    if items is not None:
        items = eval(items[0])
    else:
        items = []
    data_db.close()
    return response.json({'Response': json.dumps(items, ensure_ascii=False)})


@app.route('/api/weeklyrotations')
async def dailyrotations(request):
    data_db = sqlite3.connect('data.db')
    data_cursor = data_db.cursor()
    data_cursor.execute('''SELECT items FROM weeklyrotations''')
    items = data_cursor.fetchone()
    if items is not None:
        items = eval(items[0])
    else:
        items = []
    data_db.close()
    return response.json({'Response': json.dumps(items, ensure_ascii=False)})


@app.route('/api/seasonev')
async def seasonev(request):
    data_db = sqlite3.connect('data.db')
    data_cursor = data_db.cursor()
    data_cursor.execute('''SELECT items FROM season_ev''')
    items = data_cursor.fetchone()
    if items is not None:
        items = eval(items[0])
    else:
        items = []
    data_db.close()
    return response.json({'Response': json.dumps(items, ensure_ascii=False)})


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
                         '<form method="get" action="javascript:history.back()">\n'
                         '    <button type="submit">Вернуться назад</button>\n'
                         '</form>\n'
                         .format(item_manifest['displayProperties']['name'], item_manifest['displayProperties']['icon'],
                                 screenshot, item_manifest['displayProperties']['name'], item_manifest['displayProperties']['description']))
