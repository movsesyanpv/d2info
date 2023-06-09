from app import app, jinja
from sanic import response
from sanic.response import redirect
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


@app.route('/indeedstor')
@jinja.template('indeedstor.html')
async def index(request):
    return {}


@app.route('/bot_status')
@jinja.template('status.html')
async def status(request):
    data_db = mariadb.connect(host=api_data['db_host'], user=api_data['cache_login'],
                              password=api_data['pass'], port=api_data['db_port'],
                              database=api_data['data_db'])
    db_cursor = data_db.cursor()
    items = []
    db_cursor.execute(
        '''SELECT json, name, size, template, annotations FROM status WHERE type='daily' ORDER BY timestamp DESC''')
    data = db_cursor.fetchall()
    for item in data:
        items.append({
            'name': item[1],
            'size': item[2],
            'items': json.loads(item[0])['data'],
            'template': item[3],
            'annotations': eval(item[4])
        })

    data_db.close()
    return jinja.render('status.html', request, global_items=items)


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

    langs = request.headers.get('accept-language')

    lang = 'en'
    if langs is not None:
        if 'ru' in langs.split(';')[0].split(',')[0].replace('-', '_'):
            lang = 'ru'

    # db_cursor.execute('''SELECT json, name, size, template, annotations, background FROM {} WHERE type='daily' ORDER BY place ASC'''.format(lang))
    db_cursor.execute('''SELECT json, name, size, template, annotations FROM {} WHERE type='daily' ORDER BY place ASC'''.format(lang))
    data = db_cursor.fetchall()
    for item in data:
        items.append({
            'name': item[1],
            'size': item[2],
            'items': json.loads(item[0])['data'],
            'template': item[3],
            'annotations': eval(item[4])
        })
        # if item[5]:
        #     items[-1]['background'] = item[5]

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

    langs = request.headers.get('accept-language')

    if 'ru' in langs.split(';')[0].split(',')[0].replace('-', '_'):
        lang = 'ru'
    else:
        lang = 'en'

    db_cursor.execute('''SELECT json, name, size, template, annotations FROM {} WHERE type='weekly' ORDER BY place ASC'''.format(lang))
    data = db_cursor.fetchall()
    for item in data:
        items.append({
            'name': item[1],
            'size': item[2],
            'items': json.loads(item[0])['data'],
            'template': item[3],
            'annotations': eval(item[4])
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
async def item_legacy(request):
    return redirect('/item/{}'.format(request.args['hash'][0]))


@app.route('/item/<hash>')
async def item(request, hash):
    api_data_file = open('api.json', 'r')
    api_data = json.loads(api_data_file.read())
    d2 = pydest.Pydest(api_data['key'])

    langs = request.headers.get('accept-language')

    if 'ru' in langs.split(';')[0].split(',')[0].replace('-', '_'):
        lang = 'ru'
    else:
        lang = 'en'

    item_manifest = await d2.decode_hash(hash, 'DestinyInventoryItemDefinition', language=lang)
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


@app.route("/sitemap")
def sitemap(request):
    """
        Route to dynamically generate a sitemap of your website/application.
        lastmod and priority tags omitted on static pages.
        lastmod included on dynamic content such as blog posts.
    """
    import datetime
    from urllib.parse import urlparse

    host_components = urlparse(request.url)
    host_base = host_components.scheme + "://" + host_components.netloc

    # Static routes with static content
    static_urls = list()
    for rule in app.router.static_routes.items():
        if not rule[1].path.startswith("admin") and not rule[1].path.startswith("user"):
            if "GET" in rule[1].methods:# and len(rule.arguments) == 0:
                url = {
                    "loc": f"{host_base}/{rule[1].path}"
                }
                static_urls.append(url)

    # Dynamic routes with dynamic content
    dynamic_urls = list()
    # blog_posts = Post.objects(published=True)
    # for post in blog_posts:
    #     url = {
    #         "loc": f"{host_base}/blog/{post.category.name}/{post.url}",
    #         "lastmod": post.date_published.strftime("%Y-%m-%dT%H:%M:%SZ")
    #         }
    #     dynamic_urls.append(url)

    return jinja.render("sitemap.xml", request, static_urls=static_urls, dynamic_urls=dynamic_urls, host_base=host_base)