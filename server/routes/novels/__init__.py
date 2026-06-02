# server/routes/novels/__init__.py
from flask import Blueprint

novels_bp = Blueprint('novels', __name__)

from server.routes.novels import projects
from server.routes.novels import outline
from server.routes.novels import chapters
from server.routes.novels import entities
from server.routes.novels import events
from server.routes.novels import graph
from server.routes.novels import memories
