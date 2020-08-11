from sanic import Sanic
from sanic_jinja2 import SanicJinja2
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
import sqlite3
from urllib.parse import quote

from errorh import CustomErrorHandler
from d2data import D2data


class D2info:
    version = '0.2.1'
    sched = ''
    args = []

    logging.basicConfig()
    logging.getLogger('apscheduler').setLevel(logging.DEBUG)

    def __init__(self, **options):
        super().__init__(**options)
        self.get_args()

        self.data = D2data(self.args.production, (self.args.cert, self.args.key))

    def get_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--port', help='specify a port to listen on', default='4200')
        parser.add_argument('-p', '--production', help='Use to launch in production mode', action='store_true')
        parser.add_argument('-nm', '--nomessage', help='Don\'t post any messages', action='store_true')
        parser.add_argument('--oauth', help='Get Bungie access token', action='store_true')
        parser.add_argument('-k', '--key', help='SSL key', type=str, default='')
        parser.add_argument('-c', '--cert', help='SSL certificate', type=str, default='')
        self.args = parser.parse_args()

    async def init_data(self):
        await self.data.token_update()
        await self.data.get_chars()
        await self.data.get_seasonal_eververse()
        await self.data.get_daily_rotations()
        await self.data.get_weekly_rotations()
        await self.data.get_weekly_eververse()

    def start_up(self):

        @app.listener('before_server_start')
        async def instantiate_scheduler(app, loop):
            self.sched = AsyncIOScheduler(timezone='UTC')
            self.sched.add_job(self.init_data, misfire_grace_time=86300)
            self.sched.add_job(self.data.token_update, 'interval', hours=1)
            self.sched.add_job(self.data.get_seasonal_eververse, 'cron', day_of_week='tue', hour='17', minute='1',
                               second='40', misfire_grace_time=86300)
            self.sched.add_job(self.data.get_weekly_eververse, 'cron', day_of_week='tue', hour='17', minute='1',
                               second='40', misfire_grace_time=86300)
            self.sched.add_job(self.data.get_weekly_rotations, 'cron', day_of_week='tue', hour='17', minute='0',
                               second='40', misfire_grace_time=86300)
            self.sched.add_job(self.data.get_daily_rotations, 'cron', hour='17', minute='0', second='40',
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
