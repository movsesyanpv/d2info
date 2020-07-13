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
                'items': spider
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
                'items': heroics
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
                'items': forges
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
                'items': modifiers
            }
        return rotations

    async def get_reckoning_boss(self, lang):
        first_reset_time = 1539709200
        seconds_since_first = time.time() - first_reset_time
        weeks_since_first = seconds_since_first // 604800
        reckoning_bosses = ['swords', 'oryx']

        self.data[lang]['reckoningboss'] = {
            "thumbnail": {
                "url": "https://www.bungie.net/common/destiny2_content/icons/DestinyActivityModeDefinition_"
                       "e74b3385c5269da226372df8ae7f500d.png"
            },
            'fields': [
                {
                    'inline': True,
                    "name": self.translations[lang][reckoning_bosses[int(weeks_since_first % 2)]],
                    "value": self.translations[lang]['r_desc']
                }
            ],
            "color": 1332799,
            "type": "rich",
            "title": self.translations[lang]['msg']['reckoningboss'],
        }

    def add_reckoning_boss(self, lang):
        first_reset_time = 1539709200
        seconds_since_first = time.time() - first_reset_time
        weeks_since_first = seconds_since_first // 604800
        reckoning_bosses = ['Мечи', 'Двойник Орикса']

        return reckoning_bosses[int(weeks_since_first % 2)]

    async def get_reckoning_modifiers(self, size='wide', langs=['ru'], forceget=False):
        activities_resp = await self.get_activities_response('reckoning', string='reckoning modifiers', force=forceget)
        if not activities_resp:
            return
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
                'items': r_info
                }

    async def get_nightfall820(self, langs, forceget=False):
        activities_resp = await self.get_activities_response('nightfalls820', string='820 nightfalls', force=forceget)
        if not activities_resp:
            return
        resp_time = activities_resp['timestamp']
        for lang in langs:
            local_types = self.translations[lang]

            self.data[lang]['nightfalls820'] = {
                'thumbnail': {
                    'url': ''
                },
                'fields': [],
                'color': 7506394,
                'type': 'rich',
                'title': self.translations[lang]['msg']['nightfalls820'],
                'footer': {'text': self.translations[lang]['msg']['resp_time']},
                'timestamp': resp_time
            }

            activities_json = activities_resp
            for key in activities_json['Response']['activities']['data']['availableActivities']:
                item_hash = key['activityHash']
                definition = 'DestinyActivityDefinition'
                r_json = await self.destiny.decode_hash(item_hash, definition, language=lang)
                try:
                    recommended_light = key['recommendedLight']
                    if recommended_light == 820:
                        self.data[lang]['nightfalls820']['thumbnail']['url'] = self.icon_prefix + \
                                                                               r_json['displayProperties']['icon']
                        if r_json['matchmaking']['requiresGuardianOath']:
                            info = {
                                'inline': True,
                                'name': self.translations[lang]['msg']['guidedgamenightfall'],
                                'value': r_json['selectionScreenDisplayProperties']['name']
                            }
                        else:
                            info = {
                                'inline': True,
                                'name': r_json['selectionScreenDisplayProperties']['name'],
                                'value': r_json['selectionScreenDisplayProperties']['description']
                            }
                        self.data[lang]['nightfalls820']['fields'].append(info)
                except KeyError:
                    pass

    async def get_modifiers(self, lang, act_hash):
        url = 'https://www.bungie.net/{}/Explore/Detail/DestinyActivityDefinition/{}'.format(lang, act_hash)
        r = await self.session.get(url)
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
            return modifiers
        else:
            return False

    async def get_raids(self, langs, forceget=False):
        activities_resp = await self.get_activities_response('raids', force=forceget)
        if not activities_resp:
            return
        resp_time = activities_resp['timestamp']
        for lang in langs:
            local_types = self.translations[lang]

            self.data[lang]['raids'] = {
                'thumbnail': {
                    'url': 'https://www.bungie.net/common/destiny2_content/icons/8b1bfd1c1ce1cab51d23c78235a6e067.png'
                },
                'fields': [],
                'color': 0xF1C40F,
                'type': 'rich',
                'title': self.translations[lang]['msg']['raids'],
                'footer': {'text': self.translations[lang]['msg']['resp_time']},
                'timestamp': resp_time
            }

            first_reset_time = 1580230800
            seconds_since_first = time.time() - first_reset_time
            weeks_since_first = seconds_since_first // 604800
            eow_loadout = int(weeks_since_first % 6)
            last_wish_challenges = [1250327262, 3871581136, 1568895666, 4007940282, 2836954349]
            sotp_challenges = [1348944144, 3415614992, 1381881897]
            cos_challenges = [2459033425, 2459033426, 2459033427]
            lw_ch = 0
            sotp_ch = 0
            cos_ch = 0

            hawthorne_url = 'https://www.bungie.net/platform/Destiny2/{}/Profile/{}/Character/{}/Vendors/3347378076/'. \
                format(self.char_info['platform'], self.char_info['membershipid'], self.char_info['charid'][0])
            hawthorne_resp = await self.get_cached_json('hawthorne', 'hawthorne', hawthorne_url, self.vendor_params,
                                                        force=forceget)
            if not hawthorne_resp:
                return
            hawthorne_json = hawthorne_resp
            resp_time = hawthorne_json['timestamp']
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
                if str(r_json['hash']) in self.translations[lang]['levi_order'] and \
                        not r_json['matchmaking']['requiresGuardianOath']:
                    challenges = await self.get_modifiers(lang, item_hash)
                    if challenges:
                        challenge = set(challenges[0]['name'].lower().replace('"', '').split(' '))
                        challenge.discard('the')
                        order_strings = self.translations[lang]['levi_order'][str(r_json['hash'])].splitlines()
                        levi_str = ''
                        for string in order_strings:
                            intersection = challenge.intersection(set(string.lower().split(' ')))
                            if intersection:
                                levi_str = '{}**{}**\n'.format(levi_str, string)
                            else:
                                levi_str = '{}{}\n'.format(levi_str, string)
                        levi_str = levi_str[:-1]
                    else:
                        levi_str = self.translations[lang]['levi_order'][str(r_json['hash'])]
                    info = {
                        'inline': True,
                        'name': r_json['originalDisplayProperties']['name'],
                        'value': levi_str
                    }
                    self.data[lang]['raids']['fields'].append(info)
                if self.translations[lang]["EoW"] in r_json['displayProperties']['name'] and \
                        not r_json['matchmaking']['requiresGuardianOath']:
                    info = {
                        'inline': False,
                        'name': self.translations[lang]['lairs'],
                        'value': u"\u2063"
                    }
                    mods = await self.get_modifiers(lang, r_json['hash'])
                    resp_time = datetime.utcnow().isoformat()
                    if mods:
                        loadout = '{}\n{}\n{}'.format(self.translations[lang]['armsmaster'][eow_loadout*3],
                                                      self.translations[lang]['armsmaster'][eow_loadout*3+1],
                                                      self.translations[lang]['armsmaster'][eow_loadout*3+2])
                        info['value'] = '{}: {}\n\n{}:\n{}'.format(mods[0]['name'], mods[0]['description'],
                                                                   mods[1]['name'], loadout)
                    else:
                        info['value'] = self.data[lang]['api_is_down']['fields'][0]['name']
                    self.data[lang]['raids']['fields'].append(info)
                if self.translations[lang]['LW'] in r_json['displayProperties']['name'] and \
                        not r_json['matchmaking']['requiresGuardianOath'] and lw_ch != 0:
                    info = {
                        'inline': True,
                        'name': r_json['originalDisplayProperties']['name'],
                        'value': u"\u2063"
                    }
                    curr_challenge = lw_ch
                    curr_challenge = await self.destiny.decode_hash(curr_challenge, 'DestinyInventoryItemDefinition',
                                                                    language=lang)
                    info['value'] = curr_challenge['displayProperties']['name']
                    self.data[lang]['raids']['fields'].append(info)
                if self.translations[lang]['SotP'] in r_json['displayProperties']['name'] and \
                        not r_json['matchmaking']['requiresGuardianOath'] and sotp_ch != 0:
                    info = {
                        'inline': True,
                        'name': r_json['originalDisplayProperties']['name'],
                        'value': u"\u2063"
                    }
                    curr_challenge = sotp_ch
                    curr_challenge = await self.destiny.decode_hash(curr_challenge, 'DestinyInventoryItemDefinition',
                                                                    language=lang)
                    info['value'] = curr_challenge['displayProperties']['name']
                    self.data[lang]['raids']['fields'].append(info)
                if self.translations[lang]['CoS'] in r_json['displayProperties']['name'] and \
                        not r_json['matchmaking']['requiresGuardianOath'] and cos_ch != 0:
                    info = {
                        'inline': True,
                        'name': r_json['originalDisplayProperties']['name'],
                        'value': u"\u2063"
                    }
                    curr_challenge = cos_ch
                    curr_challenge = await self.destiny.decode_hash(curr_challenge, 'DestinyInventoryItemDefinition',
                                                                    language=lang)
                    info['value'] = curr_challenge['displayProperties']['name']
                    self.data[lang]['raids']['fields'].append(info)
                if self.translations[lang]['GoS'] in r_json['displayProperties']['name'] and \
                        not r_json['matchmaking']['requiresGuardianOath']:
                    info = {
                        'inline': True,
                        'name': r_json['originalDisplayProperties']['name'],
                        'value': u"\u2063"
                    }
                    mods = await self.get_modifiers(lang, r_json['hash'])
                    resp_time = datetime.utcnow().isoformat()
                    if mods:
                        info['value'] = mods[0]['name']
                    else:
                        info['value'] = self.data[lang]['api_is_down']['fields'][0]['name']
                    self.data[lang]['raids']['fields'].append(info)
            self.data[lang]['raids']['timestamp'] = resp_time

    async def get_ordeal(self, langs, forceget=False):
        activities_resp = await self.get_activities_response('ordeal', force=forceget)
        if not activities_resp:
            return
        resp_time = activities_resp['timestamp']
        for lang in langs:
            local_types = self.translations[lang]

            self.data[lang]['ordeal'] = {
                'thumbnail': {
                    'url': 'https://www.bungie.net/common/destiny2_content/icons/DestinyMilestoneDefinition'
                           '_a72e5ce5c66e21f34a420271a30d7ec3.png'
                },
                'fields': [],
                'color': 5331575,
                'type': 'rich',
                'title': self.translations[lang]['msg']['ordeal'],
                'footer': {'text': self.translations[lang]['msg']['resp_time']},
                'timestamp': resp_time
            }

            strikes = []

            activities_json = activities_resp
            for key in activities_json['Response']['activities']['data']['availableActivities']:
                item_hash = key['activityHash']
                definition = 'DestinyActivityDefinition'
                r_json = await self.destiny.decode_hash(item_hash, definition, language=lang)
                if r_json['activityTypeHash'] == 4110605575:
                    strikes.append({"name": r_json['displayProperties']['name'],
                                    "description": r_json['displayProperties']['description']})
                if local_types['ordeal'] in r_json['displayProperties']['name'] and \
                        local_types['adept'] in r_json['displayProperties']['name']:
                    info = {
                        'inline': True,
                        'name': r_json['originalDisplayProperties']['description'],
                        'value': u"\u2063"
                    }
                    self.data[lang]['ordeal']['fields'].append(info)

            if len(self.data[lang]['ordeal']['fields']) > 0:
                for strike in strikes:
                    if strike['name'] in self.data[lang]['ordeal']['fields'][0]['name']:
                        self.data[lang]['ordeal']['fields'][0]['value'] = strike['description']
                        break

    async def get_nightmares(self, langs, forceget=False):
        activities_resp = await self.get_activities_response('nightmares', force=forceget)
        if not activities_resp:
            return
        resp_time = activities_resp['timestamp']
        for lang in langs:
            local_types = self.translations[lang]

            self.data[lang]['nightmares'] = {
                'thumbnail': {
                    'url': 'https://www.bungie.net/common/destiny2_content/icons/DestinyActivityModeDefinition_'
                           '48ad57129cd0c46a355ef8bcaa1acd04.png'
                },
                'fields': [],
                'color': 6037023,
                'type': 'rich',
                'title': self.translations[lang]['msg']['nightmares'],
                'footer': {'text': self.translations[lang]['msg']['resp_time']},
                'timestamp': resp_time
            }

            activities_json = activities_resp
            for key in activities_json['Response']['activities']['data']['availableActivities']:
                item_hash = key['activityHash']
                definition = 'DestinyActivityDefinition'
                r_json = await self.destiny.decode_hash(item_hash, definition, language=lang)
                if local_types['nightmare'] in r_json['displayProperties']['name'] and \
                        local_types['adept'] in r_json['displayProperties']['name']:
                    info = {
                        'inline': True,
                        'name': r_json['displayProperties']['name'].replace(local_types['adept'], ""),
                        'value': r_json['displayProperties']['description']
                    }
                    self.data[lang]['nightmares']['fields'].append(info)

    async def get_crucible_rotators(self, langs, forceget=False):
        activities_resp = await self.get_activities_response('cruciblerotators', string='crucible rotators',
                                                             force=forceget)
        if not activities_resp:
            return
        resp_time = activities_resp['timestamp']
        for lang in langs:
            local_types = self.translations[lang]

            self.data[lang]['cruciblerotators'] = {
                'thumbnail': {
                    'url': self.icon_prefix + '/common/destiny2_content/icons/cc8e6eea2300a1e27832d52e9453a227.png'
                },
                'fields': [],
                'color': 6629649,
                'type': 'rich',
                'title': self.translations[lang]['msg']['cruciblerotators'],
                'footer': {'text': self.translations[lang]['msg']['resp_time']},
                'timestamp': resp_time
            }

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
                        if self.translations[lang]['rotator'] in objective['displayProperties']['name'] or r_json['challenges'][0]['objectiveHash'] == 1607758693:
                            if not self.data[lang]['cruciblerotators']['thumbnail']['url']:
                                if 'icon' in r_json['displayProperties']:
                                    self.data[lang]['cruciblerotators']['thumbnail']['url'] = self.icon_prefix + \
                                                                                              r_json[
                                                                                                  'displayProperties'][
                                                                                                  'icon']
                                else:
                                    self.data[lang]['cruciblerotators']['thumbnail']['url'] = self.icon_prefix + \
                                                                                              '/common/destiny2_content/icons/' \
                                                                                              'cc8e6eea2300a1e27832d52e9453a227.png'
                            info = {
                                'inline': True,
                                "name": r_json['displayProperties']['name'],
                                "value": r_json['displayProperties']['description']
                            }
                            self.data[lang]['cruciblerotators']['fields'].append(info)

    async def get_seasonal_eververse(self):
        tess_def = await self.destiny.decode_hash(3361454721, 'DestinyVendorDefinition')

        page = codecs.open('app/templates/ev.html', 'w', encoding='UTF8')
        page.write('{% extends \'base.html\' %}'
                   '{% block title %}Сезонный Эверверс{% endblock %}\n'
                   '{% block scripts %}'
                   '<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.5.1/jquery.min.js" defer></script>\n'
                   '<script src="/static/d2info.js" defer></script>\n'
                   '{% endblock %}'
                   '{% block meta %}'
                   '<meta name="description" content="Сезонный ассортимент Эверверс"/>\n'
                   '<meta property="og:description" content="Предметы, которые будут продаваться в этом сезоне у Тесс Эверис" />\n'
                   '<meta property="og:title" content="Сезонный Эверверс" />\n'
                   '<meta property="og:type" content="website" />\n'
                   '<meta property="og:url" content="https://d2info.happyv0dka.cloud/eververse" />\n'
                   '<meta property="og:image" content="https://bungie.net//common/destiny2_content/icons/30c6cc828d7753bcca72748ba2aa83d6.png" />\n'
                   '<link rel="icon" type="image/png" sizes="32x32" href="https://bungie.net//common/destiny2_content/icons/30c6cc828d7753bcca72748ba2aa83d6.png">\n'
                   '{% endblock %}')

        lang = 'ru'
        page.write('{{% block content %}}'
                   '<div class="global_grid">\n'
                   '<div class="global_item">\n'
                   '<h2>{}</h2>\n'
                   '<div class="wrapper">\n'.format('Популярные предметы за яркую пыль'))
        n_order = 0
        for i, item in enumerate(tess_def['itemList']):
            if item['displayCategoryIndex'] == 4 and item['itemHash'] not in [353932628, 3260482534, 3536420626,
                                                                              3187955025, 2638689062]:
                definition = 'DestinyInventoryItemDefinition'
                item_def = await self.destiny.decode_hash(item['itemHash'], definition, language=lang)
                if 'screenshot' in item_def.keys():
                    screenshot = '<img alt="Screenshot" class="screenshot_hover" src="https://bungie.net{}">'.format(
                        item_def['screenshot'])
                else:
                    screenshot = ''
                currency_resp = await self.destiny.decode_hash(item['currencies'][0]['itemHash'], definition,
                                                               language=lang)
                page.write('    <div class="item" id="{}_4_{}">\n'
                           '                <img alt="Item icon" class="icon" src="https://bungie.net{}">\n'
                           '            <div class="tooltip" id="{}_4_{}_tooltip" style="left: auto">\n'
                           '                <a class="name" href="/item/?hash={}"><b>{}</b></a><br>\n'
                           '                    {}\n'
                           '                    <img alt="Currency icon" class="currency" src="https://bungie.net{}">\n'
                           '                    <a>{}</a>\n'
                           '            </div>\n'
                           '    </div>\n'.format(item['itemHash'],
                                                 n_order,
                                                 item_def['displayProperties']['icon'],
                                                 item['itemHash'],
                                                 n_order,
                                                 item['itemHash'],
                                                 item_def['displayProperties']['name'],
                                                 screenshot,
                                                 currency_resp['displayProperties']['icon'],
                                                 item['currencies'][0]['quantity']))
                n_order += 1
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
                if 'screenshot' in item_def.keys():
                    screenshot = '<img alt="Screenshot" class="screenshot_hover" src="https://bungie.net{}">'.format(
                        item_def['screenshot'])
                else:
                    screenshot = ''
                currency_resp = await self.destiny.decode_hash(item['currencies'][0]['itemHash'], definition,
                                                               language=lang)
                page.write('    <div class="item" id="{}_9_{}">\n'
                           '                <img alt="Item icon" class="icon" src="https://bungie.net{}">\n'
                           '            <div class="tooltip" id="{}_9_{}_tooltip" style="left: auto">\n'
                           '                <a class="name" href="/item/?hash={}"><b>{}</b></a><br>\n'
                           '                    {}\n'
                           '                    <img alt="Currency icon" class="currency" src="https://bungie.net{}">\n'
                           '                    <a>{}</a>\n'
                           '            </div>\n'
                           '    </div>\n'.format(item['itemHash'],
                                                 n_order,
                                                 item_def['displayProperties']['icon'],
                                                 item['itemHash'],
                                                 n_order,
                                                 item['itemHash'],
                                                 item_def['displayProperties']['name'],
                                                 screenshot,
                                                 currency_resp['displayProperties']['icon'],
                                                 item['currencies'][0]['quantity']))
                n_order += 1

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
                if 'screenshot' in item_def.keys():
                    screenshot = '<img alt="Screenshot" class="screenshot_hover" src="https://bungie.net{}">'.format(
                        item_def['screenshot'])
                else:
                    screenshot = ''
                currency_resp = await self.destiny.decode_hash(item['currencies'][0]['itemHash'], definition,
                                                               language=lang)
                page.write('    <div class="item" id="{}_10_{}">\n'
                           '                <img alt="Item icon" class="icon" src="https://bungie.net{}">\n'
                           '            <div class="tooltip" id="{}_10_{}_tooltip" style="left: auto">\n'
                           '                <a class="name" href="/item/?hash={}"><b>{}</b></a><br>\n'
                           '                    {}\n'
                           '                    <img alt="Currency icon" class="currency" src="https://bungie.net{}">\n'
                           '                    <a>{}</a>\n'
                           '            </div>\n'
                           '    </div>\n'.format(item['itemHash'],
                                                 n_order,
                                                 item_def['displayProperties']['icon'],
                                                 item['itemHash'],
                                                 n_order,
                                                 item['itemHash'],
                                                 item_def['displayProperties']['name'],
                                                 screenshot,
                                                 currency_resp['displayProperties']['icon'],
                                                 item['currencies'][0]['quantity']))
                n_order += 1

        page.write('</div>\n'
                   '</div>\n')

        page.write('<div class="global_item">\n'
                   '<h2>{}</h2>\n'
                   '<div class="wrapper">\n'.format('Популярные предметы за серебро'))
        for i, item in enumerate(tess_def['itemList']):
            if item['displayCategoryIndex'] == 3 and item['itemHash'] != 827183327:
                definition = 'DestinyInventoryItemDefinition'
                item_def = await self.destiny.decode_hash(item['itemHash'], definition, language=lang)
                if 'screenshot' in item_def.keys():
                    screenshot = '<img alt="Screenshot" class="screenshot_hover" src="https://bungie.net{}">'.format(
                        item_def['screenshot'])
                else:
                    screenshot = ''
                currency_resp = await self.destiny.decode_hash(item['currencies'][0]['itemHash'], definition,
                                                               language=lang)
                page.write('    <div class="item" id="{}_3_{}">\n'
                           '                <img alt="Item icon" class="icon" src="https://bungie.net{}">\n'
                           '            <div class="tooltip" id="{}_3_{}_tooltip" style="left: auto">\n'
                           '                <a class="name" href="/item/?hash={}"><b>{}</b></a><br>\n'
                           '                    {}\n'
                           '                    <img alt="Currency icon" class="currency" src="https://bungie.net{}">\n'
                           '                    <a>{}</a>\n'
                           '            </div>\n'
                           '    </div>\n'.format(item['itemHash'],
                                                 n_order,
                                                 item_def['displayProperties']['icon'],
                                                 item['itemHash'],
                                                 n_order,
                                                 item['itemHash'],
                                                 item_def['displayProperties']['name'],
                                                 screenshot,
                                                 currency_resp['displayProperties']['icon'],
                                                 item['currencies'][0]['quantity']))
                n_order += 1

        page.write('</div>\n'
                   '</div>\n'
                   '</div>\n'
                   '{% endblock %}')

        page.close()

    async def get_daily_rotations(self):
        rotations = [await self.get_spider(),
                     await self.get_strike_modifiers(),
                     await self.get_reckoning_modifiers(),
                     await self.get_heroic_story(size='tall'),
                     await self.get_forge()]

        self.data_cursor.execute('''DROP TABLE dailyrotations''')
        self.data_cursor.execute('''CREATE TABLE "dailyrotations" ("items"	TEXT)''')
        self.data_cursor.execute('''INSERT into dailyrotations VALUES (?)''', (str(rotations).replace('\"', '\\\"').replace('\'', '"'),))
        self.data_db.commit()

    async def get_weekly_rotations(self):
        rotations = []
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
            rotations.append({
                'name': 'Сумрачные налеты',
                'items': nightfalls
            })

        self.data_cursor.execute('''DROP TABLE weeklyrotations''')
        self.data_cursor.execute('''CREATE TABLE "weeklyrotations" ("items"	TEXT)''')
        self.data_cursor.execute('''INSERT into weeklyrotations VALUES (?)''', (str(rotations).replace('\"', '\\\"').replace('\'', '"'),))
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

        activities_url = 'https://www.bungie.net/platform/Destiny2/{}/Profile/{}/Character/{}/'. \
            format(char_info['platform'], char_info['membershipid'], char_info['charid'][0])
        activities_resp = await self.get_bungie_json(name, activities_url, self.activities_params, lang, string)
        return activities_resp

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