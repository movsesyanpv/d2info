from sanic import Sanic
from sanic.handlers import ErrorHandler
from sanic import response
import pydest


class CustomErrorHandler(ErrorHandler):
    def default(self, request, exception):
        ''' handles errors that have no error handlers assigned '''
        # You custom error handling logic...
        if isinstance(exception, pydest.pydest.PydestException):
            return response.html('<!DOCTYPE html lang="ru">\n'
                                 '<html lang="ru">\n'
                                 '<meta name="theme-color" content="#222222">\n'
                                 '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                                 '<link rel="stylesheet" type="text/css" href="/static/style.css">\n'
                                 '<title>{}</title>\n'
                                 '<h2>Ошибка</h2>\n'
                                 '<div class="error">\n'
                                 '<a>Возникла непредвиденная ошибка при анализе манифеста.<br>\n'
                                 '</a><a class="mono">{}</a><br>'
                                 '<a>Попробуйте обновить страницу, если проблема не решится, то попробойте позже.</a>\n'
                                 '</div>'.format('Ошибка', str(exception)))
        return super().default(request, exception)
