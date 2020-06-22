from sanic import Sanic
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bungied2auth import BungieOAuth
import json
import argparse
import pydest
from app import app
import codecs
import time
import aiohttp
import logging

from errorh import CustomErrorHandler


class D2info:
    version = '0.0.1'
    sched = ''
    args = []
    headers = {}
    destiny = ''
    token = {}

    logging.basicConfig()
    logging.getLogger('apscheduler').setLevel(logging.DEBUG)

    def __init__(self, **options):
        super().__init__(**options)
        api_data_file = open('api.json', 'r')
        self.api_data = json.loads(api_data_file.read())
        self.get_args()
        if self.args.production:

            self.oauth = BungieOAuth(self.api_data['id'], self.api_data['secret'], # context=(self.args.cert, self.args.key), host='0.0.0.0',
                                     port='1423')
        else:
            self.oauth = BungieOAuth(self.api_data['id'], self.api_data['secret'], host='localhost', port='4200')

    async def token_update(self):
        # check to see if token.json exists, if not we have to start with oauth
        try:
            f = open('token.json', 'r')
        except FileNotFoundError:
            self.oauth.get_oauth()

        try:
            f = open('token.json', 'r')
            self.token = json.loads(f.read())
        except json.decoder.JSONDecodeError:
            self.oauth.get_oauth()

        # check if token has expired, if so we have to oauth, if not just refresh the token
        if self.token['expires'] < time.time():
            self.oauth.get_oauth()
        else:
            await self.refresh_token(self.token['refresh'])

    async def refresh_token(self, re_token):
        session = aiohttp.ClientSession()
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        params = {
            'grant_type': 'refresh_token',
            'refresh_token': re_token,
            'client_id': self.api_data['id'],
            'client_secret': self.api_data['secret']
        }
        r = await session.post('https://www.bungie.net/platform/app/oauth/token/', data=params, headers=headers)
        while not r:
            print("re_token get error", json.dumps(r.json(), indent=4, sort_keys=True) + "\n")
            r = await session.post('https://www.bungie.net/platform/app/oauth/token/', data=params,
                                        headers=headers)
            if not r:
                r_json = await r.json()
                if not r_json['error_description'] == 'DestinyThrottledByGameServer':
                    break
            time.sleep(5)
        await session.close()
        if not r:
            r_json = await r.json()
            print("re_token get error", json.dumps(r_json, indent=4, sort_keys=True) + "\n")
            return
        resp = await r.json()

        try:
            token = {
                'refresh': resp['refresh_token'],
                'expires': time.time() + resp['refresh_expires_in']
            }
            token_file = open('token.json', 'w')
            token_file.write(json.dumps(token))

            self.headers = {
                'X-API-Key': self.api_data['key'],
                'Authorization': 'Bearer ' + resp['access_token']
            }
        except KeyError:
            pass
        self.destiny = pydest.Pydest(self.api_data['key'])

    def get_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--port', help='specify a port to listen on', default='4200')
        parser.add_argument('-p', '--production', help='Use to launch in production mode', action='store_true')
        parser.add_argument('-nm', '--nomessage', help='Don\'t post any messages', action='store_true')
        parser.add_argument('--oauth', help='Get Bungie access token', action='store_true')
        parser.add_argument('-k', '--key', help='SSL key', type=str, default='')
        parser.add_argument('-c', '--cert', help='SSL certificate', type=str, default='')
        self.args = parser.parse_args()

    async def get_seasonal_eververse(self):
        tess_def = await self.destiny.decode_hash(3361454721, 'DestinyVendorDefinition')

        page = codecs.open('static/ev.html', 'w', encoding='UTF8')
        page.write('<!DOCTYPE html lang="ru">\n'
                   '<html lang="ru">\n'
                   '<title>Сезонный Эверверс</title>\n'
                   '<meta name="theme-color" content="#222222">\n'
                   '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                   '<link rel="stylesheet" type="text/css" href="/static/style.css">\n'
                   '<meta charset="UTF8">\n'
                   '<meta description="Сезонный ассортимент Эверверс"/>'
                   '<meta property="og:title" content="Сезонный Эверверс" />\n'
                   '<meta property="og:type" content="website" />\n'
                   '<meta property="og:url" content="https://d2info.happyv0dka.cloud/eververse" />\n'
                   '<meta property="og:image" content="https://bungie.net//common/destiny2_content/icons/30c6cc828d7753bcca72748ba2aa83d6.png" />\n'
                   '<link rel="icon" type="image/png" sizes="32x32" href="https://bungie.net//common/destiny2_content/icons/30c6cc828d7753bcca72748ba2aa83d6.png">\n')

        lang = 'ru'
        page.write('<div class="global_grid">\n'
                   '<div class="global_item">\n'
                   '<h2>{}</h2>\n'
                   '<div class="wrapper">\n'.format('Популярные предметы за яркую пыль'))
        for i, item in enumerate(tess_def['itemList']):
            if item['displayCategoryIndex'] == 4 and item['itemHash'] not in [353932628, 3260482534, 3536420626,
                                                                              3187955025, 2638689062]:
                definition = 'DestinyInventoryItemDefinition'
                item_def = await self.destiny.decode_hash(item['itemHash'], definition, language=lang)
                currency_resp = await self.destiny.decode_hash(item['currencies'][0]['itemHash'], definition,
                                                               language=lang)
                page.write('    <div class="item">\n'
                           '        <table>\n'
                           '            <tr><td>\n'
                           '                <img class="icon" src="https://bungie.net{}">\n'
                           '            </td><td>\n'
                           '                <a class="name" href="/item/?hash={}"><b>{}</b></a><br>\n'
                           # '                <div class="cost">\n'
                           '                    <img class="currency" src="https://bungie.net{}">\n'
                           '                    <a>{}</a>\n'
                           # '                </div>\n'
                           '            </td></tr>\n'
                           '        </table>\n'
                           '    </div>\n'.format(item_def['displayProperties']['icon'],
                                                 item['itemHash'],
                                                 item_def['displayProperties']['name'],
                                                 currency_resp['displayProperties']['icon'],
                                                 item['currencies'][0]['quantity']))
        page.write('</div>\n'
                   '</div>\n')

        page.write('<div class="global_item">\n'
                   '<h2>{}</h2>\n'
                   '<div class="wrapper">\n'.format('Предметы за яркую пыль'))
        for i, item in enumerate(tess_def['itemList']):
            if item['displayCategoryIndex'] == 9 and item['itemHash'] not in [353932628, 3260482534, 3536420626,
                                                                              3187955025, 2638689062]:
                definition = 'DestinyInventoryItemDefinition'
                item_def = await self.destiny.decode_hash(item['itemHash'], definition, language=lang)
                currency_resp = await self.destiny.decode_hash(item['currencies'][0]['itemHash'], definition,
                                                               language=lang)
                page.write('    <div class="item">\n'
                           '        <table>\n'
                           '            <tr><td>\n'
                           '                <img class="icon" src="https://bungie.net{}">\n'
                           '            </td><td>\n'
                           '                <a class="name" href="/item/?hash={}"><b>{}</b></a><br>\n'
                           # '                <div class="cost">\n'
                           '                    <img class="currency" src="https://bungie.net{}">\n'
                           '                    <a>{}</a>\n'
                           # '                </div>\n'
                           '            </td></tr>\n'
                           '        </table>\n'
                           '    </div>\n'.format(item_def['displayProperties']['icon'],
                                                 item['itemHash'],
                                                 item_def['displayProperties']['name'],
                                                 currency_resp['displayProperties']['icon'],
                                                 item['currencies'][0]['quantity']))
        page.write('</div>\n'
                   '</div>\n')

        page.write('<div class="global_item">\n'
                   '<h2>{}</h2>\n'
                   '<div class="wrapper">\n'.format('Потребляемые предметы за яркую пыль'))
        for i, item in enumerate(tess_def['itemList']):
            if item['displayCategoryIndex'] == 10 and item['itemHash'] not in [353932628, 3260482534, 3536420626,
                                                                               3187955025, 2638689062]:
                definition = 'DestinyInventoryItemDefinition'
                item_def = await self.destiny.decode_hash(item['itemHash'], definition, language=lang)
                currency_resp = await self.destiny.decode_hash(item['currencies'][0]['itemHash'], definition,
                                                               language=lang)
                page.write('    <div class="item">\n'
                           '        <table>\n'
                           '            <tr><td>\n'
                           '                <img class="icon" src="https://bungie.net{}">\n'
                           '            </td><td>\n'
                           '                <a class="name" href="/item/?hash={}"><b>{}</b></a><br>\n'
                           # '                <div class="cost">\n'
                           '                    <img class="currency" src="https://bungie.net{}">\n'
                           '                    <a>{}</a>\n'
                           # '                </div>\n'
                           '            </td></tr>\n'
                           '        </table>\n'
                           '    </div>\n'.format(item_def['displayProperties']['icon'],
                                                 item['itemHash'],
                                                 item_def['displayProperties']['name'],
                                                 currency_resp['displayProperties']['icon'],
                                                 item['currencies'][0]['quantity']))
        page.write('</div>\n'
                   '</div>\n')

        page.write('<div class="global_item">\n'
                   '<h2>{}</h2>\n'
                   '<div class="wrapper">\n'.format('Популярные предметы за серебро'))
        for i, item in enumerate(tess_def['itemList']):
            if item['displayCategoryIndex'] == 3 and item['itemHash'] != 827183327:
                definition = 'DestinyInventoryItemDefinition'
                item_def = await self.destiny.decode_hash(item['itemHash'], definition, language=lang)
                currency_resp = await self.destiny.decode_hash(item['currencies'][0]['itemHash'], definition,
                                                               language=lang)
                page.write('    <div class="item">\n'
                           '        <table>\n'
                           '            <tr><td>\n'
                           '                <img class="icon" src="https://bungie.net{}">\n'
                           '            </td><td>\n'
                           '                <a class="name" href="/item/?hash={}"><b>{}</b></a><br>\n'
                           # '                <div class="cost">\n'
                           '                    <img class="currency" src="https://bungie.net{}">\n'
                           '                    <a>{}</a>\n'
                           # '                </div>\n'
                           '            </td></tr>\n'
                           '        </table>\n'
                           '    </div>\n'.format(item_def['displayProperties']['icon'],
                                                 item['itemHash'],
                                                 item_def['displayProperties']['name'],
                                                 currency_resp['displayProperties']['icon'],
                                                 item['currencies'][0]['quantity']))
        page.write('</div>\n'
                   '</div>\n'
                   '</div>')

        page.close()

    async def init_data(self):
        await self.token_update()
        await self.get_seasonal_eververse()

    def start_up(self):

        @app.listener('before_server_start')
        async def instantiate_scheduler(app, loop):
            self.sched = AsyncIOScheduler(timezone='UTC')
            self.sched.add_job(self.init_data, misfire_grace_time=86300)
            self.sched.add_job(self.token_update, 'interval', hours=1)
            self.sched.add_job(self.get_seasonal_eververse, 'cron', day_of_week='tue', hour='17', minute='1',
                               second='40', misfire_grace_time=86300)
            self.sched.start()

        app.static('/static', './static')
        app.error_handler = CustomErrorHandler()
        # app.url_for('static', filename='style.css', name='style')
        if self.args.production:
            app.run(host='0.0.0.0', port=1423, workers=1, debug=False, access_log=False)  # ssl={'cert': self.args.cert, 'key': self.args.key})
        else:
            app.run()


if __name__ == '__main__':
    site = D2info()
    site.start_up()
