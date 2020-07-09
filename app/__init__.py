from sanic import Sanic
from sanic_session import Session
from sanic_jinja2 import SanicJinja2

app = Sanic(__name__)
Session(app)

jinja = SanicJinja2(app)

from app import routes
