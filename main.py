from sanic import Sanic
from jinja2 import Environment, PackageLoader, select_autoescape
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
from urllib.parse import quote

from errorh import CustomErrorHandler


class D2info:
    version = '0.0.1'
    sched = ''
    args = []
    headers = {}
    destiny = ''
    token = {}
    char_info = {}
    session = ''

    vendor_params = {
        'components': '400,401,402'
    }

    activities_params = {
        'components': '204'
    }
    wait_codes = [1672]
    max_retries = 10

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
                   '<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.5.1/jquery.min.js" async></script>\n'
                   '<script src="/static/d2info.js" async></script>\n'
                   '<meta charset="UTF8">\n'
                   '<meta name="description" content="Сезонный ассортимент Эверверс"/>\n'
                   '<meta property="og:description" content="Предметы, которые будут продаваться в этом сезоне у Тесс Эверис" />\n'
                   '<meta property="og:title" content="Сезонный Эверверс" />\n'
                   '<meta property="og:type" content="website" />\n'
                   '<meta property="og:url" content="https://d2info.happyv0dka.cloud/eververse" />\n'
                   '<meta property="og:image" content="https://bungie.net//common/destiny2_content/icons/30c6cc828d7753bcca72748ba2aa83d6.png" />\n'
                   '<link rel="icon" type="image/png" sizes="32x32" href="https://bungie.net//common/destiny2_content/icons/30c6cc828d7753bcca72748ba2aa83d6.png">\n'
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
                   '<div class="header-fixed-placeholder"></div>\n')

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
                page.write('    <div class="item" id="{}_4">\n'
                           '                <img alt="Item icon" class="icon" src="https://bungie.net{}">\n'
                           '            <div class="tooltip" id="{}_4_tooltip" style="left: auto">\n'
                           '                <a class="name" href="/item/?hash={}"><b>{}</b></a><br>\n'
                           '                    <img alt="Currency icon" class="currency" src="https://bungie.net{}">\n'
                           '                    <a>{}</a>\n'
                           '            </div>\n'
                           '    </div>\n'.format(item['itemHash'],
                                                 item_def['displayProperties']['icon'],
                                                 item['itemHash'],
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
                page.write('    <div class="item" id="{}_9">\n'
                           '                <img alt="Item icon" class="icon" src="https://bungie.net{}">\n'
                           '            <div class="tooltip" id="{}_9_tooltip" style="left: auto">\n'
                           '                <a class="name" href="/item/?hash={}"><b>{}</b></a><br>\n'
                           '                    <img alt="Currency icon" class="currency" src="https://bungie.net{}">\n'
                           '                    <a>{}</a>\n'
                           '            </div>\n'
                           '    </div>\n'.format(item['itemHash'],
                                                 item_def['displayProperties']['icon'],
                                                 item['itemHash'],
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
                page.write('    <div class="item" id="{}_10">\n'
                           '                <img alt="Item icon" class="icon" src="https://bungie.net{}">\n'
                           '            <div class="tooltip" id="{}_10_tooltip" style="left: auto">\n'
                           '                <a class="name" href="/item/?hash={}"><b>{}</b></a><br>\n'
                           '                    <img alt="Currency icon" class="currency" src="https://bungie.net{}">\n'
                           '                    <a>{}</a>\n'
                           '            </div>\n'
                           '    </div>\n'.format(item['itemHash'],
                                                 item_def['displayProperties']['icon'],
                                                 item['itemHash'],
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
                page.write('    <div class="item" id="{}_3">\n'
                           '                <img alt="Item icon" class="icon" src="https://bungie.net{}">\n'
                           '            <div class="tooltip" id="{}_3_tooltip" style="left: auto">\n'
                           '                <a class="name" href="/item/?hash={}"><b>{}</b></a><br>\n'
                           '                    <img alt="Currency icon" class="currency" src="https://bungie.net{}">\n'
                           '                    <a>{}</a>\n'
                           '            </div>\n'
                           '    </div>\n'.format(item['itemHash'],
                                                 item_def['displayProperties']['icon'],
                                                 item['itemHash'],
                                                 item['itemHash'],
                                                 item_def['displayProperties']['name'],
                                                 currency_resp['displayProperties']['icon'],
                                                 item['currencies'][0]['quantity']))
        page.write('</div>\n'
                   '</div>\n'
                   '</div>\n'
                   '<script>enableTooltips()</script>')

        page.close()

    async def get_daily_rotations(self):
        activities_resp = await self.get_activities_response('vanguardstrikes', string='strike modifiers')

        page = codecs.open('static/daily.html', 'w', encoding='UTF8')
        page.write('<!DOCTYPE html lang="ru">\n'
                   '<html lang="ru">\n'
                   '<title>Сегодня в игре</title>\n'
                   '<meta name="theme-color" content="#222222">\n'
                   '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                   '<link rel="stylesheet" type="text/css" href="/static/style.css">\n'
                   '<meta charset="UTF8">\n'
                   '<meta name="description" content="Информация о ежедневном сбросе Destiny 2"/>\n'
                   '<meta property="og:description" content="Информация о ежедневном сбросе Destiny 2" />\n'
                   '<meta property="og:title" content="Сегодня в игре" />\n'
                   '<meta property="og:type" content="website" />\n'
                   '<meta property="og:url" content="https://d2info.happyv0dka.cloud/daily" />\n'
                   '<meta property="og:image" content="https://bungie.net//common/destiny2_content/icons/30c6cc828d7753bcca72748ba2aa83d6.png" />\n'
                   '<link rel="icon" type="image/png" sizes="32x32" href="https://bungie.net//common/destiny2_content/icons/30c6cc828d7753bcca72748ba2aa83d6.png">\n'
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
                   '<div class="header-fixed-placeholder"></div>\n')
        lang = 'ru'
        page.write('<div class="global_grid">\n'
                   '<div class="global_item">\n'
                   '<h2>{}</h2>\n'
                   '<div class="wrapper">\n'.format('Модификаторы плейлиста налетов'))
        activities_json = activities_resp
        modifiers = []
        for key in activities_json['Response']['activities']['data']['availableActivities']:
            item_hash = key['activityHash']
            definition = 'DestinyActivityDefinition'
            r_json = await self.destiny.decode_hash(item_hash, definition, language=lang)

            if 'Ежедневная героическая сюжетная миссия: ' in r_json['displayProperties']['name']:
                modifiers = await self.decode_modifiers(key, lang)
        for mod in modifiers:
            page.write('    <div class="item">\n'
                       '        <table>\n'
                       '            <tr><td>\n'
                       '                <img alt="Item icon" class="icon" src="https://bungie.net{}">\n'
                       '            </td><td>\n'
                       '                <a class="name"><b>{}</b></a><br>\n'
                       '                    <a>{}</a>\n'
                       '            </td></tr>\n'
                       '        </table>\n'
                       '    </div>\n'.format(mod['icon'],
                                             mod['name'],
                                             mod['description']))
        page.write('</div>\n'
                   '</div>\n'
                   '</div>')
        page.close()

    async def decode_modifiers(self, key, lang):
        data = []
        for mod_key in key['modifierHashes']:
            mod_def = 'DestinyActivityModifierDefinition'
            mod_json = await self.destiny.decode_hash(mod_key, mod_def, lang)
            mod = {
                "icon": mod_json['displayProperties']['icon'],
                "name": mod_json['displayProperties']['name'],
                "description": mod_json['displayProperties']['description']
            }
            data.append(mod)
        return data

    async def get_activities_response(self, name, lang=None, string=None, force=False):
        char_info = self.char_info

        activities_url = 'https://www.bungie.net/platform/Destiny2/{}/Profile/{}/Character/{}/'. \
            format(char_info['platform'], char_info['membershipid'], char_info['charid'][0])
        activities_resp = await self.get_bungie_json(name, activities_url, self.activities_params, lang, string)
        return activities_resp

    async def get_bungie_json(self, name, url, params=None, lang=None, string=None, change_msg=True):
        session = aiohttp.ClientSession()
        if lang is None:
            lang_str = 'ru'
        else:
            lang_str = lang
        if string is None:
            string = str(name)
        try:
            resp = await session.get(url, params=params, headers=self.headers)
        except:
            return False
        try:
            resp_code = await resp.json()
            resp_code = resp_code['ErrorCode']
        except KeyError:
            resp_code = 1
        except json.decoder.JSONDecodeError:
            return False
        except aiohttp.ContentTypeError:
            return False
        print('getting {} {}'.format(string, lang_str))
        curr_try = 2
        while resp_code in self.wait_codes and curr_try <= self.max_retries:
            print('{}, attempt {}'.format(resp_code, curr_try))
            resp = await session.get(url, params=params, headers=self.headers)
            try:
                resp_code = await resp.json()
                resp_code = resp_code['ErrorCode']
            except aiohttp.ContentTypeError:
                resp_code = 1672
            if resp_code == 5:
                curr_try -= 1
            curr_try += 1
            time.sleep(5)
        if not resp:
            try:
                resp_code = await resp.json()
            except aiohttp.ContentTypeError:
                return False
            resp_code = resp_code['ErrorCode']
            if resp_code == 5:
                return False
            print("{} get error".format(name), json.dumps(resp.json(), indent=4, sort_keys=True) + "\n")
            return False
        else:
            try:
                resp_code = await resp.json()
            except aiohttp.ContentTypeError:
                return False
            if 'ErrorCode' in resp_code.keys():
                resp_code = resp_code['ErrorCode']
                if resp_code == 5:
                    return False
            else:
                for suspected_season in resp_code:
                    if 'seasonNumber' in resp_code[suspected_season].keys():
                        return resp_code
        await session.close()
        return await resp.json()

    async def get_chars(self):
        session = aiohttp.ClientSession()
        platform = 0
        membership_id = ''
        try:
            char_file = open('char.json', 'r')
            self.char_info = json.loads(char_file.read())
        except FileNotFoundError:
            valid_input = False
            while not valid_input:
                print("What platform are you playing on?")
                print("1. Xbox")
                print("2. Playstation")
                print("3. Steam")
                platform = int(input())
                if 3 >= platform >= 1:
                    valid_input = True
            platform = str(platform)
            self.char_info['platform'] = platform

            valid_input = False
            while not valid_input:
                name = input("What's the name of your account on there? (include # numbers): ")
                search_url = 'https://www.bungie.net/platform/Destiny2/SearchDestinyPlayer/' + str(
                    platform) + '/' + quote(
                    name) + '/'
                search_resp = await session.get(search_url, headers=self.headers)
                search_json = await search_resp.json()
                search = search_json['Response']
                if len(search) > 0:
                    valid_input = True
                    membership_id = search[0]['membershipId']
                    self.char_info['membershipid'] = membership_id

            char_search_url = 'https://www.bungie.net/platform/Destiny2/' + platform + '/Profile/' + membership_id + '/'
            char_search_params = {
                'components': '200'
            }
            char_search_resp = await session.get(char_search_url, params=char_search_params, headers=self.headers)
            char_search_json = await char_search_resp.json()
            chars = char_search_json['Response']['characters']['data']
            char_ids = []
            for key in sorted(chars.keys()):
                char_ids.append(chars[key]['characterId'])
            self.char_info['charid'] = char_ids

            char_file = open('char.json', 'w')
            char_file.write(json.dumps(self.char_info))
            await session.close()

    async def init_data(self):
        await self.token_update()
        await self.get_chars()
        await self.get_seasonal_eververse()
        await self.get_daily_rotations()

    def start_up(self):

        @app.listener('before_server_start')
        async def instantiate_scheduler(app, loop):
            self.sched = AsyncIOScheduler(timezone='UTC')
            self.sched.add_job(self.init_data, misfire_grace_time=86300)
            self.sched.add_job(self.token_update, 'interval', hours=1)
            self.sched.add_job(self.get_seasonal_eververse, 'cron', day_of_week='tue', hour='17', minute='1',
                               second='40', misfire_grace_time=86300)
            self.sched.add_job(self.get_daily_rotations, 'cron', hour='17', minute='0', second='40',
                               misfire_grace_time=86300)
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
