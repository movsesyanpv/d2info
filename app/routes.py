from app import app
from sanic import response
import pydest


@app.route('/')
@app.route('/eververse')
async def eververse(request):
    return await response.file('static/ev.html')
