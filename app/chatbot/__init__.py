from flask import Blueprint

chatbot = Blueprint('chatbot', __name__)

from . import views
