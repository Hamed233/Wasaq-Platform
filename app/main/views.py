from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from . import main
from app.models.user import User
from app.models.land import Land
from app.models.report import Report
from app.models.recommendation import Recommendation
from app.models.statistic import Statistic
from flask_login import login_required, current_user
from app import db

@main.route('/')
def index():
    """Landing page with overview of the platform"""
    return render_template('index.html')

@main.route('/map')
def map_view():
    """Interactive GIS map view of all endowment lands"""
    lands = Land.query.all()
    map_center = [current_app.config['MAP_CENTER_LAT'], current_app.config['MAP_CENTER_LNG']]
    map_zoom = current_app.config['MAP_DEFAULT_ZOOM']
    return render_template('map.html', lands=lands, map_center=map_center, map_zoom=map_zoom)

@main.route('/about')
def about():
    """About page with information about the platform"""
    return render_template('about.html')

@main.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')

@main.route('/faq')
def faq():
    """Frequently asked questions"""
    return render_template('faq.html')

@main.route('/search')
def search():
    """Search for endowment lands"""
    query = request.args.get('q', '')
    region = request.args.get('region', '')
    land_type = request.args.get('type', '')
    status = request.args.get('status', '')
    
    lands_query = Land.query
    
    if query:
        lands_query = lands_query.filter(Land.name.contains(query) | 
                                         Land.description.contains(query))
    if region:
        lands_query = lands_query.filter(Land.region == region)
    if land_type:
        lands_query = lands_query.filter(Land.land_type == land_type)
    if status:
        lands_query = lands_query.filter(Land.status == status)
    
    lands = lands_query.all()
    return render_template('search_results.html', lands=lands, query=query)
