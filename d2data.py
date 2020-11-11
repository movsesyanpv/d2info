import json
import time
from urllib.parse import quote
import pydest
from bs4 import BeautifulSoup
from bungied2auth import BungieOAuth
from datetime import datetime, timezone, timedelta
from dateutil.parser import *
import aiohttp
import sqlite3
import matplotlib.pyplot as plt
import csv
import codecs


class D2data:
    api_data_file = open('api.json', 'r')
    api_data = json.loads(api_data_file.read())
    destiny = ''

    cache_db = ''
    data_db = sqlite3.connect('data.db')
    data_cursor = data_db.cursor()

    icon_prefix = "https://www.bungie.net"

    token = {}

    headers = {}

    data = {}

    wait_codes = [1672]
    max_retries = 10

    vendor_params = {
        'components': '400,401,402'
    }

    activities_params = {
        'components': '204'
    }

    record_params = {
        "components": "900,700"
    }

    metric_params = {
        "components": "1100"
    }

    char_info = {}

    def __init__(self, prod, context, **options):
        super().__init__(**options)
        if prod:
            self.oauth = BungieOAuth(self.api_data['id'], self.api_data['secret'], context=context, host='0.0.0.0',
                                     port='4200')
        else:
            self.oauth = BungieOAuth(self.api_data['id'], self.api_data['secret'], host='localhost', port='4200')
        self.session = aiohttp.ClientSession()
        self.cache_db = sqlite3.connect('cache.db')
        try:
            self.data_cursor.execute('''CREATE TABLE "dailyrotations" ("items"	TEXT)''')
        except sqlite3.OperationalError:
            pass
        try:
            self.data_cursor.execute('''CREATE TABLE "weeklyrotations" ("items"	TEXT)''')
        except sqlite3.OperationalError:
            pass
        try:
            self.data_cursor.execute('''CREATE TABLE "season_ev" ("items"	TEXT)''')
        except sqlite3.OperationalError:
            pass
        try:
            self.data_cursor.execute('''CREATE TABLE "evweekly" ("items"	TEXT)''')
        except sqlite3.OperationalError:
            pass
        self.data_db.commit()

    async def get_spider(self, size='tall', langs=['ru'], forceget=False):
        char_info = self.char_info
        rotations = {}
        lang = 'ru'

        spider_url = 'https://www.bungie.net/platform/Destiny2/{}/Profile/{}/Character/{}/Vendors/863940356/'. \
            format(char_info['platform'], char_info['membershipid'], char_info['charid'][0])
        spider_resp = await self.get_bungie_json('spider', spider_url, self.vendor_params, string='spider')
        if spider_resp:
            spider_json = spider_resp
            spider_cats = spider_json['Response']['categories']['data']['categories']
            spider_def = await self.destiny.decode_hash(863940356, 'DestinyVendorDefinition', language=lang)

            items_to_get = spider_cats[0]['itemIndexes']

            spider = await self.get_vendor_sales(lang, spider_resp, items_to_get, [1812969468])

            rotations = {
                'name': 'Паук',
                'size': size,
                'items': spider,
                'template': 'table_items.html'
            }
        return rotations

    async def get_xur_loc(self):
        url = 'https://wherethefuckisxur.com/'
        r = await self.session.get(url)
        r_text = await r.text()
        soup = BeautifulSoup(r_text, features="html.parser")
        modifier_list = soup.find('div', {'class': 'xur-location'})
        loc = modifier_list.find('h1', {'class': 'page-title'})
        location = loc.text.split(' >')
        return location[0]

    async def get_xur(self, langs=['ru'], forceget=False):
        char_info = self.char_info

        xur_url = 'https://www.bungie.net/platform/Destiny2/{}/Profile/{}/Character/{}/Vendors/2190858386/'. \
            format(char_info['platform'], char_info['membershipid'], char_info['charid'][0])
        xur_resp = await self.get_bungie_json('xur', xur_url, self.vendor_params)
        if not xur_resp:
            return {}
        for lang in langs:

            xur_def = await self.destiny.decode_hash(2190858386, 'DestinyVendorDefinition', language=lang)
            self.data[lang]['xur'] = {
                'thumbnail': {
                    'url': self.icon_prefix + xur_def['displayProperties']['smallTransparentIcon']
                },
                'fields': [],
                'color': 0x3DD5D6,
                'type': "rich",
                'title': self.translations[lang]['msg']['xurtitle'],
                'footer': {'text': self.translations[lang]['msg']['resp_time']},
                'timestamp': resp_time
            }

            xur_json = xur_resp
            if not xur_json['ErrorCode'] == 1627:
                loc_field = {
                    "inline": False,
                    "name": self.translations[lang]['msg']['xurloc'],
                    "value": self.translations[lang]['xur']['NULL']
                }
                weapon = {
                    'inline': False,
                    'name': self.translations[lang]['msg']['weapon'],
                    'value': ''
                }
                try:
                    loc_field['value'] = self.translations[lang]['xur'][await self.get_xur_loc()]
                    self.data[lang]['xur']['fields'].append(loc_field)
                except:
                    pass
                xur_sales = xur_json['Response']['sales']['data']

                self.data[lang]['xur']['fields'].append(weapon)

                for key in sorted(xur_sales.keys()):
                    item_hash = xur_sales[key]['itemHash']
                    if item_hash not in [4285666432, 2293314698]:
                        definition = 'DestinyInventoryItemDefinition'
                        item_resp = await self.destiny.decode_hash(item_hash, definition, language=lang)
                        item_name = item_resp['displayProperties']['name']
                        if item_resp['itemType'] == 2:
                            item_sockets = item_resp['sockets']['socketEntries']
                            plugs = []
                            for s in item_sockets:
                                if len(s['reusablePlugItems']) > 0 and s['plugSources'] == 2:
                                    plugs.append(s['reusablePlugItems'][0]['plugItemHash'])

                            exotic = {
                                'inline': True,
                                'name': '',
                                'value': item_name
                            }

                            if item_resp['classType'] == 0:
                                exotic['name'] = self.translations[lang]['Titan']
                            elif item_resp['classType'] == 1:
                                exotic['name'] = self.translations[lang]['Hunter']
                            elif item_resp['classType'] == 2:
                                exotic['name'] = self.translations[lang]['Warlock']

                            self.data[lang]['xur']['fields'].append(exotic)
                        else:
                            i = 0
                            for item in self.data[lang]['xur']['fields']:
                                if item['name'] == self.translations[lang]['msg']['weapon']:
                                    self.data[lang]['xur']['fields'][i]['value'] = item_name
                                i += 1
            else:
                loc_field = {
                    "inline": False,
                    "name": self.translations[lang]['msg']['xurloc'],
                    "value": self.translations[lang]['xur']['noxur']
                }
                self.data[lang]['xur']['fields'].append(loc_field)

    async def get_heroic_story(self, size='wide', langs=['ru'], forceget=False):
        activities_resp = await self.get_activities_response('heroicstory', string='heroic story missions',
                                                             force=forceget)
        if not activities_resp:
            return {}
        for lang in langs:
            heroics = []

            activities_json = activities_resp
            for key in activities_json['Response']['activities']['data']['availableActivities']:
                item_hash = key['activityHash']
                definition = 'DestinyActivityDefinition'
                r_json = await self.destiny.decode_hash(item_hash, definition, language=lang)

                if 'Ежедневная героическая сюжетная миссия: ' in r_json['displayProperties']['name']:
                    info = {
                        "name": r_json['selectionScreenDisplayProperties']['name'],
                        "description": r_json['selectionScreenDisplayProperties']['description']
                    }
                    heroics.append(info)
            return {
                'name': 'Героические сюжетные миссии',
                'size': size,
                'items': heroics,
                'template': 'table_items.html'
            }

    async def get_forge(self, size='', langs=['ru'], forceget=False):
        activities_resp = await self.get_activities_response('forge', force=forceget)
        if not activities_resp:
            return {}
        for lang in langs:
            forges = []
            activities_json = activities_resp
            for key in activities_json['Response']['activities']['data']['availableActivities']:
                item_hash = key['activityHash']
                definition = 'DestinyActivityDefinition'
                r_json = await self.destiny.decode_hash(item_hash, definition, language=lang)

                if 'Кузница' in r_json['displayProperties']['name']:
                    forge_def = 'DestinyDestinationDefinition'
                    place = await self.destiny.decode_hash(r_json['destinationHash'], forge_def, language=lang)
                    info = {
                        "icon": r_json['displayProperties']['icon'],
                        "name": r_json['displayProperties']['name'],
                        "description": place['displayProperties']['name']
                    }
                    forges.append(info)
            rotations = {
                'name': 'Кузница',
                'size': size,
                'items': forges,
                'template': 'table_items.html'
            }
        return rotations

    async def get_strike_modifiers(self, size='wide', langs=['ru'], forceget=False):
        char_info = self.char_info
        activities_resp = await self.get_activities_response('vanguardstrikes', string='strike modifiers')

        lang = 'ru'
        rotations = {}
        if activities_resp:
            activities_json = activities_resp
            modifiers = []
            for key in activities_json['Response']['activities']['data']['availableActivities']:
                item_hash = key['activityHash']
                definition = 'DestinyActivityDefinition'
                r_json = await self.destiny.decode_hash(item_hash, definition, language=lang)

                if 'Ежедневная героическая сюжетная миссия: ' in r_json['displayProperties']['name']:
                    modifiers = await self.decode_modifiers(key, lang)
            rotations = {
                'name': 'Модификаторы плейлиста налетов',
                'size': size,
                'items': modifiers,
                'template': 'table_items.html'
            }
        return rotations

    def add_reckoning_boss(self, lang):
        first_reset_time = 1539709200
        seconds_since_first = time.time() - first_reset_time
        weeks_since_first = seconds_since_first // 604800
        reckoning_bosses = ['Мечи', 'Двойник Орикса']

        return reckoning_bosses[int(weeks_since_first % 2)]

    async def get_reckoning_modifiers(self, size='wide', langs=['ru'], forceget=False):
        activities_resp = await self.get_activities_response('reckoning', string='reckoning modifiers', force=forceget)
        if not activities_resp:
            return {}
        for lang in langs:
            r_info = {
                'icon': '/common/destiny2_content/icons/'
                        'DestinyActivityModeDefinition_e74b3385c5269da226372df8ae7f500d.png',
                'name': 'Босс',
                'description': self.add_reckoning_boss(lang)
            }

            activities_json = activities_resp
            for key in activities_json['Response']['activities']['data']['availableActivities']:
                item_hash = key['activityHash']
                definition = 'DestinyActivityDefinition'
                r_json = await self.destiny.decode_hash(item_hash, definition, language=lang)

                if 'Суд: Уровень III' in r_json['displayProperties']['name']:
                    mods = await self.decode_modifiers(key, lang)
                    r_info = [r_info, *mods]
            return {
                'name': 'Суд',
                'size': size,
                'items': r_info,
                'template': 'table_items.html'
                }

    async def get_nightfall820(self, size='', langs=['ru'], forceget=False):
        lang = 'ru'

        activities_resp = await self.get_activities_response('nightfalls820', string='820 nightfalls')
        if activities_resp:
            activities_json = activities_resp
            nightfalls = []
            for key in activities_json['Response']['activities']['data']['availableActivities']:
                item_hash = key['activityHash']
                definition = 'DestinyActivityDefinition'
                r_json = await self.destiny.decode_hash(item_hash, definition, language=lang)
                try:
                    recommended_light = key['recommendedLight']
                    if recommended_light == 820:
                        if r_json['matchmaking']['requiresGuardianOath']:
                            info = {
                                'name': 'Сумрак с гидом',
                                'description': r_json['selectionScreenDisplayProperties']['name']
                            }
                        else:
                            info = {
                                'name': r_json['selectionScreenDisplayProperties']['name'],
                                'description': r_json['selectionScreenDisplayProperties']['description']
                            }
                        nightfalls.append(info)
                except KeyError:
                    pass
            return {
                'name': 'Сумрачные налеты',
                'size': size,
                'items': nightfalls,
                'template': 'table_items.html'
            }
        else:
            return {}

    async def get_modifiers(self, lang, act_hash):
        url = 'https://www.bungie.net/{}/Explore/Detail/DestinyActivityDefinition/{}'.format(lang, act_hash)
        session = aiohttp.ClientSession()
        r = await session.get(url)
        r = await r.text()
        soup = BeautifulSoup(r, features="html.parser")
        modifier_list = soup.find_all('div', {'data-identifier': 'modifier-information'})
        modifiers = []
        for item in modifier_list:
            modifier = item.find('div', {'class': 'text-content'})
            modifier_title = modifier.find('div', {'class': 'title'})
            modifier_subtitle = modifier.find('div', {'class': 'subtitle'})
            mod = {
                "name": modifier_title.text,
                "description": modifier_subtitle.text
            }
            modifiers.append(mod)
        if r:
            await session.close()
            return modifiers
        else:
            await session.close()
            return False

    async def get_raids(self, size='wide tall', langs=['ru'], forceget=False):
        activities_resp = await self.get_activities_response('raids', force=forceget)
        if not activities_resp:
            return {}
        raids = []
        for lang in langs:

            first_reset_time = 1580230800
            seconds_since_first = time.time() - first_reset_time
            weeks_since_first = seconds_since_first // 604800
            eow_loadout = int(weeks_since_first % 6)
            last_wish_challenges = [1250327262, 3871581136, 1568895666, 4007940282, 2836954349]
            sotp_challenges = [1348944144, 3415614992, 1381881897]
            cos_challenges = [2459033425, 2459033426, 2459033427]
            levi_order = {
                "417231112": "1. Сады удовольствий<br>\n2. Турнир<br>\n3. Королевские бассейны<br>\n4. Трон",
                "757116822": "1. Турнир<br>\n2. Королевские бассейны<br>\n3. Сады удовольствий<br>\n4. Трон",
                "1685065161": "1. Турнир<br>\n2. Сады удовольствий<br>\n3. Королевские бассейны<br>\n4. Трон",
                "2449714930": "1. Королевские бассейны<br>\n2. Турнир<br>\n3. Сады удовольствий<br>\n4. Трон",
                "3446541099": "1. Сады удовольствий<br>\n2. Королевские бассейны<br>\n3. Турнир<br>\n4. Трон",
                "3879860661": "1. Королевские бассейны<br>\n2. Сады удовольствий<br>\n3. Турнир<br>\n4. Трон"
            }
            eow_loadouts = [
                "Кинетическое: Револьвер", "Энергетическое: Снайперская винтовка", "Силовое: Любое",
                "Кинетическое: Автомат", "Энергетическое: Автомат", "Силовое: Любое",
                "Кинетическое: Пистолет", "Энергетическое: Винтовка разведчика", "Силовое: Меч",
                "Кинетическое: Пистолет-пулемет", "Энергетическое: Любое", "Силовое: Гранатомет",
                "Кинетическое: Любое", "Энергетическое: Плазменная винтовка", "Силовое: Плазменная винтовка",
                "Кинетическое: Дробовик", "Энергетическое: Автомат", "Силовое: Ракетная установка"
            ]
            lw_ch = 0
            sotp_ch = 0
            cos_ch = 0

            hawthorne_url = 'https://www.bungie.net/platform/Destiny2/{}/Profile/{}/Character/{}/Vendors/3347378076/'. \
                format(self.char_info['platform'], self.char_info['membershipid'], self.char_info['charid'][0])
            hawthorne_resp = await self.get_bungie_json('hawthorne', hawthorne_url, self.vendor_params)
            if not hawthorne_resp:
                return
            hawthorne_json = hawthorne_resp
            for cat in hawthorne_json['Response']['sales']['data']:
                if hawthorne_json['Response']['sales']['data'][cat]['itemHash'] in last_wish_challenges:
                    lw_ch = hawthorne_json['Response']['sales']['data'][cat]['itemHash']
                elif hawthorne_json['Response']['sales']['data'][cat]['itemHash'] in sotp_challenges:
                    sotp_ch = hawthorne_json['Response']['sales']['data'][cat]['itemHash']
                elif hawthorne_json['Response']['sales']['data'][cat]['itemHash'] in cos_challenges:
                    cos_ch = hawthorne_json['Response']['sales']['data'][cat]['itemHash']

            activities_json = activities_resp
            for key in activities_json['Response']['activities']['data']['availableActivities']:
                item_hash = key['activityHash']
                definition = 'DestinyActivityDefinition'
                r_json = await self.destiny.decode_hash(item_hash, definition, language=lang)
                i = 1
                if str(r_json['hash']) in levi_order.keys() and \
                        not r_json['matchmaking']['requiresGuardianOath']:
                    challenges = await self.get_modifiers(lang, item_hash)
                    if challenges:
                        challenge = set(challenges[0]['name'].lower().replace('"', '').split(' '))
                        challenge.discard('the')
                        order_strings = levi_order[str(r_json['hash'])].splitlines()
                        levi_str = ''
                        for string in order_strings:
                            intersection = challenge.intersection(set(string.lower().split(' ')))
                            if intersection:
                                levi_str = '{}<b>{}</b>\n'.format(levi_str, string)
                            else:
                                levi_str = '{}{}\n'.format(levi_str, string)
                        levi_str = levi_str[:-1]
                    else:
                        levi_str = levi_order[str(r_json['hash'])]
                    info = {
                        'name': r_json['originalDisplayProperties']['name'],
                        'description': levi_str
                    }
                    raids.append(info)
                if 'пожиратель миров: Престиж' in r_json['displayProperties']['name'] and \
                        not r_json['matchmaking']['requiresGuardianOath']:
                    info = {
                        'inline': False,
                        'name': 'Пожиратель Миров и Звездный Шпиль',
                        'description': u"\u2063"
                    }
                    mods = await self.get_modifiers(lang, r_json['hash'])
                    resp_time = datetime.utcnow().isoformat()
                    if mods:
                        loadout = '{}<br>\n{}\n<br>{}'.format(eow_loadouts[eow_loadout*3], eow_loadouts[eow_loadout*3+1],
                                                      eow_loadouts[eow_loadout*3+2])
                        info['description'] = '{}: {}\n<br>\n{}:\n<br>{}'.format(mods[0]['name'], mods[0]['description'],
                                                                   mods[1]['name'], loadout)
                    raids.append(info)
                if 'Последнее желание' in r_json['displayProperties']['name'] and \
                        not r_json['matchmaking']['requiresGuardianOath'] and lw_ch != 0:
                    info = {
                        'name': r_json['originalDisplayProperties']['name'],
                        'description': u"\u2063"
                    }
                    curr_challenge = lw_ch
                    curr_challenge = await self.destiny.decode_hash(curr_challenge, 'DestinyInventoryItemDefinition',
                                                                    language=lang)
                    info['description'] = curr_challenge['displayProperties']['name']
                    raids.append(info)
                if 'Истребители прошлого' in r_json['displayProperties']['name'] and \
                        not r_json['matchmaking']['requiresGuardianOath'] and sotp_ch != 0:
                    info = {
                        'name': r_json['originalDisplayProperties']['name'],
                        'description': u"\u2063"
                    }
                    curr_challenge = sotp_ch
                    curr_challenge = await self.destiny.decode_hash(curr_challenge, 'DestinyInventoryItemDefinition',
                                                                    language=lang)
                    info['description'] = curr_challenge['displayProperties']['name']
                    raids.append(info)
                if 'Корона скорби' in r_json['displayProperties']['name'] and \
                        not r_json['matchmaking']['requiresGuardianOath'] and cos_ch != 0:
                    info = {
                        'name': r_json['originalDisplayProperties']['name'],
                        'descripition': u"\u2063"
                    }
                    curr_challenge = cos_ch
                    curr_challenge = await self.destiny.decode_hash(curr_challenge, 'DestinyInventoryItemDefinition',
                                                                    language=lang)
                    info['description'] = curr_challenge['displayProperties']['name']
                    raids.append(info)
                if 'Сад спасения' in r_json['displayProperties']['name'] and \
                        not r_json['matchmaking']['requiresGuardianOath']:
                    info = {
                        'name': r_json['originalDisplayProperties']['name'],
                        'description': u"\u2063"
                    }
                    mods = await self.get_modifiers(lang, r_json['hash'])
                    if mods:
                        info['description'] = mods[0]['name']
                    raids.append(info)
        return {
            'name': 'Рейды',
            'size': size,
            'items': raids,
            'template': 'table_items.html'
        }

    async def get_ordeal(self, size='', langs=['ru'], forceget=False):
        activities_resp = await self.get_activities_response('ordeal', force=forceget)
        if not activities_resp:
            return {}
        for lang in langs:
            strikes = []
            ordeal = []

            activities_json = activities_resp
            for key in activities_json['Response']['activities']['data']['availableActivities']:
                item_hash = key['activityHash']
                definition = 'DestinyActivityDefinition'
                r_json = await self.destiny.decode_hash(item_hash, definition, language=lang)
                if r_json['activityTypeHash'] == 4110605575:
                    strikes.append({"name": r_json['displayProperties']['name'],
                                    "description": r_json['displayProperties']['description']})
                if 'Сумрачный налет: Побоище' in r_json['displayProperties']['name'] and \
                        ': Мастер' in r_json['displayProperties']['name']:
                    info = {
                        'name': r_json['originalDisplayProperties']['description'],
                        'description': u"\u2063"
                    }
                    ordeal.append(info)

            if info:
                for strike in strikes:
                    if strike['name'] in info['name']:
                        info['description'] = strike['description']
                        break
            return {
                'name': 'Сумрачный налет: Побоище',
                'size': size,
                'items': ordeal,
                'template': 'table_items.html'
            }

    async def get_nightmares(self, size='', langs=['ru'], forceget=False):
        activities_resp = await self.get_activities_response('nightmares', force=forceget)
        if not activities_resp:
            return {}
        for lang in langs:
            nightmares = []
            activities_json = activities_resp
            for key in activities_json['Response']['activities']['data']['availableActivities']:
                item_hash = key['activityHash']
                definition = 'DestinyActivityDefinition'
                r_json = await self.destiny.decode_hash(item_hash, definition, language=lang)
                if 'Охота на кошмаров:' in r_json['displayProperties']['name'] and \
                        ': Мастер' in r_json['displayProperties']['name']:
                    info = {
                        'name': r_json['displayProperties']['name'].replace(': Мастер', "").replace('Охота на кошмаров: ', '').replace('\"', ''),
                        'description': r_json['displayProperties']['description']
                    }
                    nightmares.append(info)
            return {
                'name': 'Охоты на кошмаров',
                'size': size,
                'items': nightmares,
                'template': 'table_items.html'
            }

    async def get_crucible_rotators(self, size='wide', langs=['ru'], forceget=False):
        activities_resp = await self.get_activities_response('cruciblerotators', string='crucible rotators',
                                                             force=forceget)
        if not activities_resp:
            return {}
        rotators = []
        for lang in langs:
            activities_json = activities_resp
            for key in activities_json['Response']['activities']['data']['availableActivities']:
                item_hash = key['activityHash']
                definition = 'DestinyActivityDefinition'
                r_json = await self.destiny.decode_hash(item_hash, definition, language=lang)
                if r_json['destinationHash'] == 2777041980:
                    if len(r_json['challenges']) > 0:
                        obj_def = 'DestinyObjectiveDefinition'
                        objective = await self.destiny.decode_hash(r_json['challenges'][0]['objectiveHash'], obj_def,
                                                                   lang)
                        if 'Испытание из сменяемого плейлиста Горнила' in objective['displayProperties']['name'] or r_json['challenges'][0]['objectiveHash'] == 1607758693:
                            if 'icon' in r_json['displayProperties']:
                                icon = r_json['displayProperties']['icon']
                            else:
                                icon = ''
                            info = {
                                'icon': icon,
                                "name": r_json['displayProperties']['name'],
                                "description": r_json['displayProperties']['description'].replace('\n\n', '<br>')
                            }
                            if 'icon' in r_json['displayProperties']:
                                info['icon'] = r_json['displayProperties']['icon']
                            else:
                                info['icon'] = '/common/destiny2_content/icons/cc8e6eea2300a1e27832d52e9453a227.png'
                            rotators.append(info)
        return {
            'name': 'Сменяемые режимы горнила',
            'size': size,
            'items': rotators,
            'template': 'table_items.html'
        }

    async def get_seasonal_eververse(self):
        tess_def = await self.destiny.decode_hash(3361454721, 'DestinyVendorDefinition')

        data = [
            {
                'name': 'Популярные предметы за яркую пыль',
                'items': []
            },
            {
                'name': 'Предметы за яркую пыль',
                'items': []
            },
            {
                'name': 'Потребляемые предметы за яркую пыль',
                'items': []
            },
            {
                'name': 'Яркие энграммы',
                'items': []
            },
            {
                'name': 'Популярные предметы за серебро',
                'items': []
            }]

        lang = 'ru'
        n_order = 0
        for i, item in enumerate(tess_def['itemList']):
            definition = 'DestinyInventoryItemDefinition'
            item_def = await self.destiny.decode_hash(item['itemHash'], definition, language=lang)
            if 'screenshot' in item_def.keys():
                screenshot = '<img alt="Screenshot" class="screenshot_hover" src="https://bungie.net{}"' \
                             'loading="lazy">'.format(item_def['screenshot'])
            else:
                screenshot = ''
            is_interesting = False
            if item['displayCategoryIndex'] == 2 and item['itemHash'] not in [353932628, 3260482534, 3536420626,
                                                                              3187955025, 2638689062]:
                is_interesting = True
                cat_number = 2
                data_index = 0
            elif item['displayCategoryIndex'] == 7 and item['itemHash'] not in [353932628, 3260482534, 3536420626,
                                                                                3187955025, 2638689062]:
                is_interesting = True
                cat_number = 7
                data_index = 1
            elif item['displayCategoryIndex'] == 8 and item['itemHash'] not in [353932628, 3260482534, 3536420626,
                                                                                 3187955025, 2638689062]:
                is_interesting = True
                cat_number = 9
                data_index = 2
            elif item['displayCategoryIndex'] == 1 and item['itemHash'] != 827183327:
                is_interesting = True
                cat_number = 1
                data_index = 4
            if is_interesting:
                currency_resp = await self.destiny.decode_hash(item['currencies'][0]['itemHash'], definition,
                                                               language=lang)
                data[data_index]['items'].append({
                    'id': '{}_{}_{}'.format(item['itemHash'], cat_number, n_order),
                    'icon': item_def['displayProperties']['icon'],
                    'tooltip_id': '{}_{}_{}_tooltip'.format(item['itemHash'], cat_number, n_order),
                    'hash': item['itemHash'],
                    'name': item_def['displayProperties']['name'],
                    'screenshot': screenshot,
                    'currency_icon': currency_resp['displayProperties']['icon'],
                    'cost': item['currencies'][0]['quantity'],
                    'currency': currency_resp['displayProperties']['name']
                })
                n_order += 1
        engram_def = await self.destiny.decode_hash(tess_def['itemList'][-1]['itemHash'], 'DestinyInventoryItemDefinition', 'ru')
        for category in engram_def['preview']['derivedItemCategories'][0]['items']:
            cat_def = await self.destiny.decode_hash(category['itemHash'], 'DestinyInventoryItemDefinition', 'ru')
            for cat_preview in cat_def['preview']['derivedItemCategories']:
                for engram_item in cat_preview['items']:
                    item_def = await self.destiny.decode_hash(engram_item['itemHash'], definition, language=lang)
                    if 'screenshot' in item_def.keys():
                        screenshot = '<img alt="Screenshot" class="screenshot_hover" src="https://bungie.net{}" ' \
                                     'loading="lazy">'.format(item_def['screenshot'])
                    else:
                        screenshot = ''
                    data[3]['items'].append({
                        'id': '{}_{}_{}'.format(engram_item['itemHash'], 1337, n_order),
                        'icon': item_def['displayProperties']['icon'],
                        'tooltip_id': '{}_{}_{}_tooltip'.format(engram_item['itemHash'], 1337, n_order),
                        'hash': engram_item['itemHash'],
                        'name': item_def['displayProperties']['name'],
                        'screenshot': screenshot,
                        'currency_icon': engram_def['displayProperties']['icon'],
                        'cost': 1,
                        'currency': engram_def['displayProperties']['name']
                    })
                    n_order += 1
        self.data_cursor.execute('''DROP TABLE season_ev''')
        self.data_cursor.execute('''CREATE TABLE "season_ev" ("items"	TEXT)''')
        self.data_cursor.execute('''INSERT into season_ev VALUES (?)''',
                                 (str(data).replace('\"', '\\\"').replace('\'', '"'),))
        self.data_db.commit()

    async def get_season_start(self):
        manifest_url = 'https://www.bungie.net/Platform/Destiny2/Manifest/'
        manifest_json = await self.get_bungie_json('default', manifest_url, {}, '')
        season_url = 'https://www.bungie.net{}'.format(
            manifest_json['Response']['jsonWorldComponentContentPaths']['en']['DestinySeasonDefinition'])
        season_json = await self.get_bungie_json('default', season_url, {}, '')

        for season in season_json:
            try:
                start = isoparse(season_json[season]['startDate'])
                end = isoparse(season_json[season]['endDate'])
                if start <= datetime.now(tz=timezone.utc) <= end:
                    current_season = season
                    return start
            except KeyError:
                pass
        return datetime.now(tz=timezone.utc)

    async def get_seasonal_featured_silver(self, langs, start):
        tess_def = await self.destiny.decode_hash(3361454721, 'DestinyVendorDefinition')

        for lang in langs:
            self.data[lang]['seasonal_silver'].clear()

            data = {
                'thumbnail': {
                    'url': self.icon_prefix + '/common/destiny2_content/icons/30c6cc828d7753bcca72748ba2aa83d6.png'
                },
                'fields': [],
                'color': 0x38479F,
                'type': "rich",
                'title': self.translations[lang]['msg']['silver'],
            }

            n_items = 0
            curr_week = dict.copy(data)
            i_week = 1
            class_items = 0
            for i, item in enumerate(tess_def['itemList']):
                if n_items == 25:
                    curr_week['title'] = '{}{} {}'.format(self.translations[lang]['msg']['silver'],
                                                          self.translations[lang]['msg']['week'], i_week)
                    i_week = i_week + 1
                    self.data[lang]['seasonal_silver'].append(dict.copy(curr_week))
                    n_items = 0
                    curr_week['fields'] = []
                    class_items = 0
                if item['displayCategoryIndex'] == 3 and item['itemHash'] != 827183327:
                    definition = 'DestinyInventoryItemDefinition'
                    item_def = await self.destiny.decode_hash(item['itemHash'], definition, language=lang)
                    currency_resp = await self.destiny.decode_hash(item['currencies'][0]['itemHash'], definition,
                                                                   language=lang)
                    currency_cost = str(item['currencies'][0]['quantity'])
                    currency_item = currency_resp['displayProperties']['name']
                    item_data = {
                        'inline': True,
                        'name': item_def['displayProperties']['name'],
                        'value': "{}: {} {}".format(self.translations[lang]['msg']['cost'], currency_cost,
                                                    currency_item.capitalize())
                    }
                    curr_week['fields'].append(item_data)
                    n_items = n_items + 1
                    if item_def['classType'] < 3 or any(
                            class_name in item_def['itemTypeDisplayName'].lower() for class_name in
                            ['hunter', 'warlock', 'titan']):
                        class_items = class_items + 1

    async def get_seasonal_featured_bd(self, langs, start):
        tess_def = await self.destiny.decode_hash(3361454721, 'DestinyVendorDefinition')

        bd = []
        classnames = ["охотник", "варлок", "титан"]

        for lang in langs:

            n_items = 0
            curr_week = []
            i_week = 1
            class_items = 0
            n_order = 0
            for i, item in enumerate(tess_def['itemList']):
                if n_items >= 4 and n_items - class_items / 3 * 2 >= 4:
                    i_week = i_week + 1
                    bd.append(list.copy(curr_week))
                    n_items = 0
                    curr_week = []
                    class_items = 0
                if item['displayCategoryIndex'] == 2 and item['itemHash'] not in [353932628, 3260482534, 3536420626,
                                                                                  3187955025, 2638689062]:
                    definition = 'DestinyInventoryItemDefinition'
                    item_def = await self.destiny.decode_hash(item['itemHash'], definition, language=lang)
                    currency_resp = await self.destiny.decode_hash(item['currencies'][0]['itemHash'], definition,
                                                                   language=lang)
                    cat_number = 4
                    if 'screenshot' in item_def.keys():
                        screenshot = '<img alt="Screenshot" class="screenshot_hover" src="https://bungie.net{}"' \
                                     'loading="lazy">'.format(item_def['screenshot'])
                    else:
                        screenshot = ''
                    curr_week.append({
                        'id': '{}_{}_{}'.format(item['itemHash'], cat_number, n_order),
                        'icon': item_def['displayProperties']['icon'],
                        'tooltip_id': '{}_{}_{}_tooltip'.format(item['itemHash'], cat_number, n_order),
                        'hash': item['itemHash'],
                        'name': item_def['displayProperties']['name'],
                        'screenshot': screenshot,
                        'currency_icon': currency_resp['displayProperties']['icon'],
                        'cost': item['currencies'][0]['quantity'],
                        'currency': currency_resp['displayProperties']['name']
                    })
                    n_order += 1
                    n_items = n_items + 1
                    if item_def['classType'] < 3 or any(
                            class_name in item_def['itemTypeDisplayName'].lower() for class_name in classnames):
                        class_items = class_items + 1
        return bd

    async def get_seasonal_consumables(self, langs, start):
        tess_def = await self.destiny.decode_hash(3361454721, 'DestinyVendorDefinition')

        for lang in langs:
            self.data[lang]['seasonal_consumables'].clear()

            data = {
                'thumbnail': {
                    'url': self.icon_prefix + '/common/destiny2_content/icons/30c6cc828d7753bcca72748ba2aa83d6.png'
                },
                'fields': [],
                'color': 0x38479F,
                'type': "rich",
                'title': self.translations[lang]['msg']['bd_consumables'],
            }

            n_items = 0
            curr_week = dict.copy(data)
            i_week = 1
            class_items = 0
            for i, item in enumerate(tess_def['itemList']):
                if n_items == 25:
                    curr_week['title'] = '{}{} {}'.format(self.translations[lang]['msg']['bd_consumables'],
                                                          self.translations[lang]['msg']['week'], i_week)
                    i_week = i_week + 1
                    self.data[lang]['seasonal_consumables'].append(dict.copy(curr_week))
                    n_items = 0
                    curr_week['fields'] = []
                    class_items = 0
                if item['displayCategoryIndex'] == 8 and item['itemHash'] not in [353932628, 3260482534, 3536420626,
                                                                                   3187955025, 2638689062]:
                    definition = 'DestinyInventoryItemDefinition'
                    item_def = await self.destiny.decode_hash(item['itemHash'], definition, language=lang)
                    currency_resp = await self.destiny.decode_hash(item['currencies'][0]['itemHash'], definition,
                                                                   language=lang)
                    currency_cost = str(item['currencies'][0]['quantity'])
                    currency_item = currency_resp['displayProperties']['name']
                    item_data = {
                        'inline': True,
                        'name': item_def['displayProperties']['name'],
                        'value': "{}: {} {}".format(self.translations[lang]['msg']['cost'], currency_cost,
                                                    currency_item.capitalize())
                    }
                    curr_week['fields'].append(item_data)
                    n_items = n_items + 1
                    if item_def['classType'] < 3 or any(
                            class_name in item_def['itemTypeDisplayName'].lower() for class_name in
                            ['hunter', 'warlock', 'titan']):
                        class_items = class_items + 1

    async def get_seasonal_bd(self, langs, start):
        tess_def = await self.destiny.decode_hash(3361454721, 'DestinyVendorDefinition')

        bd = []
        classnames = ["охотник", "варлок", "титан"]

        for lang in langs:

            n_items = 0
            curr_week = []
            i_week = 1
            class_items = 0
            n_order = 0
            for i, item in enumerate(tess_def['itemList']):
                if n_items >= 7 and n_items - class_items/3*2 >= 7:
                    i_week = i_week + 1
                    bd.append(list.copy(curr_week))
                    n_items = 0
                    curr_week = []
                    class_items = 0
                if item['displayCategoryIndex'] == 7 and item['itemHash'] not in [353932628, 3260482534, 3536420626,
                                                                                  3187955025, 2638689062]:
                    definition = 'DestinyInventoryItemDefinition'
                    item_def = await self.destiny.decode_hash(item['itemHash'], definition, language=lang)
                    currency_resp = await self.destiny.decode_hash(item['currencies'][0]['itemHash'], definition,
                                                                   language=lang)
                    cat_number = 9
                    if 'screenshot' in item_def.keys():
                        screenshot = '<img alt="Screenshot" class="screenshot_hover" src="https://bungie.net{}" ' \
                                     'loading="lazy">'.format(item_def['screenshot'])
                    else:
                        screenshot = ''
                    curr_week.append({
                            'id': '{}_{}_{}'.format(item['itemHash'], cat_number, n_order),
                            'icon': item_def['displayProperties']['icon'],
                            'tooltip_id': '{}_{}_{}_tooltip'.format(item['itemHash'], cat_number, n_order),
                            'hash': item['itemHash'],
                            'name': item_def['displayProperties']['name'],
                            'screenshot': screenshot,
                            'currency_icon': currency_resp['displayProperties']['icon'],
                            'cost': item['currencies'][0]['quantity'],
                            'currency': currency_resp['displayProperties']['name']
                        })
                    n_order += 1
                    n_items = n_items + 1
                    if item_def['classType'] < 3 or any(
                            class_name in item_def['itemTypeDisplayName'].lower() for class_name in classnames):
                        class_items = class_items + 1
        return bd

    async def get_weekly_eververse(self):
        langs = ['ru']
        data = []
        start = await self.get_season_start()
        bd = await self.get_seasonal_bd(langs, start)
        featured_bd = await self.get_seasonal_featured_bd(langs, start)
        # await self.get_seasonal_consumables(langs, start)
        # await self.get_seasonal_featured_silver(langs, start)
        week_n = datetime.now(tz=timezone.utc) - await self.get_season_start()
        week_n = int(week_n.days / 7)
        if len(bd) == len(featured_bd):
            for i in range(0, len(bd)):
                if week_n == i:
                    week_str = 'Неделя {} (текущая)'.format(i + 1)
                else:
                    week_str = 'Неделя {}'.format(i + 1)
                data.append({
                    'name': week_str,
                    'items': [*bd[i], *featured_bd[i]]
                })

        self.data_cursor.execute('''DROP TABLE evweekly''')
        self.data_cursor.execute('''CREATE TABLE "evweekly" ("items"	TEXT)''')
        self.data_cursor.execute('''INSERT into evweekly VALUES (?)''',
                                 (str(data).replace('\"', '\\\"').replace('\'', '"'),))
        self.data_db.commit()
        return {
                'name': 'Эверверс',
                'size': '',
                'items': data[week_n]['items'],
                'template': 'hover_items.html'
            }

    async def get_daily_rotations(self):
        rotations = [await self.get_spider(),
                     await self.get_strike_modifiers(),
                     await self.get_reckoning_modifiers(),
                     await self.get_heroic_story(size='tall'),
                     await self.get_forge()]

        n_rotations = []
        for rotation in rotations:
            if rotation:
                n_rotations.append(rotation)

        self.data_cursor.execute('''DROP TABLE dailyrotations''')
        self.data_cursor.execute('''CREATE TABLE "dailyrotations" ("items"	TEXT)''')
        self.data_cursor.execute('''INSERT into dailyrotations VALUES (?)''', (str(n_rotations).replace('\"', '\\\"').replace('\'', '"'),))
        self.data_db.commit()

    async def get_weekly_rotations(self):
        rotations = [await self.get_nightfall820(),
                     await self.get_raids(),
                     await self.get_weekly_eververse(),
                     await self.get_nightmares(),
                     await self.get_crucible_rotators(),
                     await self.get_ordeal()]

        n_rotations = []
        for rotation in rotations:
            if rotation:
                n_rotations.append(rotation)

        self.data_cursor.execute('''DROP TABLE weeklyrotations''')
        self.data_cursor.execute('''CREATE TABLE "weeklyrotations" ("items"	TEXT)''')
        self.data_cursor.execute('''INSERT into weeklyrotations VALUES (?)''', (str(n_rotations).replace('\"', '\\\"').replace('\'', '"'),))
        self.data_db.commit()

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
        activities = []
        hashes = set()

        for char in char_info['charid']:
            activities_url = 'https://www.bungie.net/platform/Destiny2/{}/Profile/{}/Character/{}/'. \
                format(char_info['platform'], char_info['membershipid'], char)
            activities_resp = await self.get_cached_json('activities_{}'.format(char), name, activities_url,
                                                         self.activities_params, lang, string, force=force)
            if activities_resp:
                activities.append(activities_resp)
        activities_json = await self.get_cached_json('activities_{}'.format(char_info['charid'][-1]), name,
                                                     activities_url, self.activities_params, lang, string, force=force)

        if activities_json:
            activities_json['Response']['activities']['data']['availableActivities'].clear()

        if len(activities) == 0:
            return False
        else:
            if len(activities) > 0:
                for char_activities in activities:
                    for activity in char_activities['Response']['activities']['data']['availableActivities']:
                        if activity['activityHash'] not in hashes:
                            activities_json['Response']['activities']['data']['availableActivities'].append(activity)
                            hashes.add(activity['activityHash'])
            return activities_json

    async def get_vendor_sales(self, lang, vendor_resp, cats, exceptions=[]):
        embed_sales = []

        vendor_json = vendor_resp
        tess_sales = vendor_json['Response']['sales']['data']
        for key in cats:
            item = tess_sales[str(key)]
            item_hash = item['itemHash']
            if item_hash not in exceptions:
                definition = 'DestinyInventoryItemDefinition'
                item_resp = await self.destiny.decode_hash(item_hash, definition, language=lang)
                item_name_list = item_resp['displayProperties']['name'].split()
                item_name = ' '.join(item_name_list)
                if len(item['costs']) > 0:
                    currency = item['costs'][0]
                    currency_resp = await self.destiny.decode_hash(currency['itemHash'], definition, language=lang)

                    currency_cost = str(currency['quantity'])
                    currency_item = currency_resp['displayProperties']['name']
                else:
                    currency_cost = 'N/A'
                    currency_item = ''

                item_data = {
                    'icon': item_resp['displayProperties']['icon'],
                    'name': item_name.capitalize(),
                    'description': "{}: {} {}".format('Цена', currency_cost,
                                                currency_item.capitalize())
                }
                embed_sales.append(item_data)
        return embed_sales

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
            membership_url = 'https://www.bungie.net/platform/User/GetMembershipsForCurrentUser/'
            search_resp = await session.get(url=membership_url, headers=self.headers)
            search_json = await search_resp.json()
            self.char_info['membershipid'] = search_json['Response']['primaryMembershipId']
            membership_id = search_json['Response']['primaryMembershipId']
            for membership in search_json['Response']['destinyMemberships']:
                if membership['membershipId'] == self.char_info['membershipid']:
                    platform = membership['membershipType']
            self.char_info['platform'] = platform

            char_search_url = 'https://www.bungie.net/platform/Destiny2/{}/Profile/{}/'.format(platform, membership_id)
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

    async def get_cached_json(self, cache_id, name, url, params=None, lang=None, string=None, change_msg=True,
                              force=False, cache_only=False):
        cache_cursor = self.cache_db.cursor()

        try:
            cache_cursor.execute('''SELECT json, expires, timestamp from cache WHERE id=?''', (cache_id,))
            cached_entry = cache_cursor.fetchone()
            if cached_entry is not None:
                expired = datetime.now().timestamp() > cached_entry[1]
            else:
                expired = True
        except sqlite3.OperationalError:
            expired = True
            if cache_only:
                return False

        if (expired or force) and not cache_only:
            response = await self.get_bungie_json(name, url, params, lang, string, change_msg)
            timestamp = datetime.utcnow().isoformat()
            if response:
                response_json = response
                try:
                    cache_cursor.execute(
                        '''CREATE TABLE cache (id text, expires integer, json text, timestamp text);''')
                    cache_cursor.execute('''CREATE UNIQUE INDEX cache_id ON cache(id)''')
                    cache_cursor.execute('''INSERT OR IGNORE INTO cache VALUES (?,?,?,?)''',
                                         (cache_id, int(datetime.now().timestamp() + 1800), json.dumps(response_json),
                                          timestamp))
                except sqlite3.OperationalError:
                    try:
                        cache_cursor.execute('''ALTER TABLE cache ADD COLUMN timestamp text''')
                        cache_cursor.execute('''INSERT OR IGNORE INTO cache VALUES (?,?,?,?)''',
                                             (cache_id, int(datetime.now().timestamp() + 1800),
                                              json.dumps(response_json), timestamp))
                    except sqlite3.OperationalError:
                        pass
                try:
                    cache_cursor.execute('''INSERT OR IGNORE INTO cache VALUES (?,?,?,?)''',
                                         (cache_id, int(datetime.now().timestamp() + 1800), json.dumps(response_json),
                                          timestamp))
                except sqlite3.OperationalError:
                    pass
                try:
                    cache_cursor.execute('''UPDATE cache SET expires=?, json=?, timestamp=? WHERE id=?''',
                                         (int(datetime.now().timestamp() + 1800), json.dumps(response_json), timestamp,
                                          cache_id))
                except sqlite3.OperationalError:
                    pass
            else:
                return False
        else:
            timestamp = cached_entry[2]
            response_json = json.loads(cached_entry[0])
        self.cache_db.commit()
        response_json['timestamp'] = timestamp
        return response_json

