from flask import Blueprint

lands = Blueprint('lands', __name__)

from . import views
