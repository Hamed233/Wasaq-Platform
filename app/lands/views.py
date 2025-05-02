from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from . import lands
from app.models.land import Land
from app.models.report import Report
from app.models.recommendation import Recommendation
from app.models.statistic import Statistic
from app.models.user import User
from app import db
from app.ai.recommendation_model import RecommendationModel
import json
from datetime import datetime
import os
import random
from sqlalchemy import func

@lands.route('/')
@login_required
def index():
    """List all endowment lands with filtering and pagination"""
    # Get filter parameters
    region = request.args.get('region')
    land_type = request.args.get('type')
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    
    # Check if we have any lands in the database
    lands_count = Land.query.count()
    
    # If no lands exist, add demo data
    if lands_count == 0:
        ensure_demo_data()
    
    # Build query
    query = Land.query
    
    if region and region.strip():
        query = query.filter_by(region=region)
    if land_type and land_type.strip():
        query = query.filter_by(land_type=land_type)
    if status and status.strip():
        query = query.filter_by(status=status)
    
    # Get lands with pagination
    lands_per_page = current_app.config.get('LANDS_PER_PAGE', 10)
    lands_pagination = query.paginate(page=page, per_page=lands_per_page, error_out=False)
    lands = lands_pagination.items
    
    # Get unique regions, types, and statuses for filter dropdowns
    regions = db.session.query(Land.region).distinct().all()
    land_types = db.session.query(Land.land_type).distinct().all()
    statuses = db.session.query(Land.status).distinct().all()
    
    # Get summary statistics
    total_lands = Land.query.count()
    total_area = db.session.query(func.sum(Land.area)).scalar() or 0
    total_income = db.session.query(func.sum(Land.yearly_income)).scalar() or 0
    avg_return = db.session.query(func.avg(Land.annual_return)).scalar() or 0
    
    # Calculate status percentages and counts for the progress bar
    status_counts = {
        'available': Land.query.filter_by(status='available').count(),
        'invested': Land.query.filter_by(status='invested').count(),
        'under_development': Land.query.filter_by(status='under_development').count(),
        'other': Land.query.filter(~Land.status.in_(['available', 'invested', 'under_development'])).count()
    }
    
    total_count = sum(status_counts.values())
    status_percentages = {
        'available': round(status_counts['available'] / total_count * 100) if total_count > 0 else 0,
        'invested': round(status_counts['invested'] / total_count * 100) if total_count > 0 else 0,
        'under_development': round(status_counts['under_development'] / total_count * 100) if total_count > 0 else 0,
        'other': round(status_counts['other'] / total_count * 100) if total_count > 0 else 0
    }
    
    return render_template(
        'lands/index.html',
        lands=lands,
        pagination=lands_pagination,
        regions=[r[0] for r in regions if r[0]],
        land_types=[t[0] for t in land_types if t[0]],
        statuses=[s[0] for s in statuses if s[0]],
        selected_region=region,
        selected_type=land_type,
        selected_status=status,
        total_lands=total_lands,
        total_area=total_area,
        total_income=total_income,
        avg_return=avg_return,
        status_counts=status_counts,
        status_percentages=status_percentages
    )

@lands.route('/map')
@login_required
def map_view():
    """Show the map with all lands"""
    # Get filter parameters
    region = request.args.get('region')
    land_type = request.args.get('type')
    status = request.args.get('status')
    
    # Check if we have any lands in the database
    lands_count = Land.query.count()
    
    # If no lands exist, add demo data
    if lands_count == 0:
        ensure_demo_data()
    
    # Build query
    query = Land.query
    
    if region and region.strip():
        query = query.filter_by(region=region)
    if land_type and land_type.strip():
        query = query.filter_by(land_type=land_type)
    if status and status.strip():
        query = query.filter_by(status=status)
    
    # Get lands
    lands = query.all()
    
    # Get unique regions, types, and statuses for filter dropdowns
    regions = db.session.query(Land.region).distinct().all()
    land_types = db.session.query(Land.land_type).distinct().all()
    statuses = db.session.query(Land.status).distinct().all()
    
    # Calculate summary statistics
    total_lands = len(lands)
    total_area = sum(land.area for land in lands if land.area)
    total_income = sum(land.yearly_income for land in lands if land.yearly_income)
    avg_return = sum(land.annual_return for land in lands if land.annual_return) / len(lands) if lands else 0
    
    # Prepare GeoJSON data
    features = []
    for land in lands:
        popup_content = f"""
        <div class='map-popup'>
            <h5>{land.name}</h5>
            <p><strong>المنطقة:</strong> {land.region}</p>
            <p><strong>المدينة:</strong> {land.city}</p>
            <p><strong>المساحة:</strong> {'{:,}'.format(land.area)} م²</p>
            <p><strong>النوع:</strong> {land.land_type}</p>
            <p><strong>الحالة:</strong> 
                {'متاحة للاستثمار' if land.status == 'available' else 'قيد الاستثمار' if land.status == 'invested' else 'قيد التطوير' if land.status == 'under_development' else land.status}
            </p>
            <a href='{url_for('lands.view', land_id=land.id)}' class='btn btn-sm btn-primary'>عرض التفاصيل</a>
        </div>
        """
        
        feature = {
            "type": "Feature",
            "properties": {
                "name": land.name,
                "status": land.status,
                "type": land.land_type,
                "region": land.region,
                "city": land.city,
                "area": land.area,
                "popup_content": popup_content
            },
            "geometry": {
                "type": "Point",
                "coordinates": [land.longitude, land.latitude]
            }
        }
        features.append(feature)
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    # Get map center from config or default to Riyadh
    map_center = {
        "lat": float(current_app.config.get('MAP_CENTER_LAT', 24.7136)),
        "lng": float(current_app.config.get('MAP_CENTER_LNG', 46.6753)),
        "zoom": int(current_app.config.get('MAP_DEFAULT_ZOOM', 6))
    }
    
    # If we have lands and are filtering by region, center the map on that region
    if lands and region and region.strip():
        # Calculate average coordinates of filtered lands
        avg_lat = sum(land.latitude for land in lands if land.latitude) / len(lands)
        avg_lng = sum(land.longitude for land in lands if land.longitude) / len(lands)
        map_center = {
            "lat": float(avg_lat),
            "lng": float(avg_lng),
            "zoom": 8  # Zoom in more when filtering by region
        }
    
    return render_template('lands/map.html', 
                           geojson=geojson, 
                           map_center=map_center,
                           regions=[r[0] for r in regions if r[0]],
                           land_types=[t[0] for t in land_types if t[0]],
                           statuses=[s[0] for s in statuses if s[0]],
                           selected_region=region,
                           selected_type=land_type,
                           selected_status=status,
                           total_lands=total_lands,
                           total_area=total_area,
                           total_income=total_income,
                           avg_return=avg_return)

@lands.route('/<int:land_id>')
@login_required
def view(land_id):
    """View a specific endowment land with its details"""
    # Check if we have any lands in the database
    lands_count = Land.query.count()
    
    # If no lands exist, add demo data
    if lands_count == 0:
        ensure_demo_data()
        # If we're trying to view a land that doesn't exist yet, redirect to index
        if not Land.query.get(land_id):
            return redirect(url_for('lands.index'))
    
    # Get the land
    land = Land.query.get_or_404(land_id)
    
    # Get recommendations, reports, and statistics for this land
    recommendations = Recommendation.query.filter_by(land_id=land.id).all()
    reports = Report.query.filter_by(land_id=land.id).all()
    
    # Get statistics grouped by category
    statistics = {}
    stats = Statistic.query.filter_by(land_id=land.id).all()
    for stat in stats:
        if stat.category not in statistics:
            statistics[stat.category] = []
        statistics[stat.category].append(stat)
    
    return render_template('lands/view.html', land=land, recommendations=recommendations, reports=reports, statistics=statistics)

@lands.route('/<int:land_id>/generate-recommendations')
@login_required
def generate_recommendations(land_id):
    """Generate AI recommendations for a specific land"""
    if not current_user.is_admin():
        flash('غير مسموح لك بتنفيذ هذه الإجراء', 'danger')
        return redirect(url_for('lands.view', land_id=land_id))
    
    land = Land.query.get_or_404(land_id)
    
    # Initialize recommendation model
    model_path = os.path.join(current_app.root_path, 'ai', 'models', 'recommendation_model.joblib')
    
    try:
        # Check if model exists, otherwise train a new one
        if os.path.exists(model_path):
            model = RecommendationModel(model_path=model_path)
        else:
            # For demo purposes, we'll create recommendations without a trained model
            model = RecommendationModel()
        
        # Generate recommendations
        recommendations_data = model.generate_recommendations(land.to_dict())
        
        # Save recommendations to database
        for rec_data in recommendations_data:
            recommendation = Recommendation(
                title=rec_data['title'],
                description=rec_data['description'],
                recommendation_type=rec_data['recommendation_type'],
                priority=rec_data['priority'],
                status='pending',
                confidence_score=rec_data['confidence_score'],
                estimated_cost=rec_data['estimated_cost'],
                estimated_return=rec_data['estimated_return'],
                estimated_timeframe=rec_data['estimated_timeframe'],
                land_id=land.id,
                user_id=current_user.id,
                supporting_data=rec_data['supporting_data'],
                ai_model_version=rec_data['ai_model_version']
            )
            db.session.add(recommendation)
        
        db.session.commit()
        flash('تم إنشاء التوصيات بنجاح', 'success')
    
    except Exception as e:
        db.session.rollback()
        flash(f'خطأ عند إنشاء التوصيات: {str(e)}', 'danger')
    
    return redirect(url_for('lands.view', land_id=land_id))

@lands.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a new endowment land"""
    if not current_user.is_admin():
        flash('غير مسموح لك بتنفيذ هذه الإجراء', 'danger')
        return redirect(url_for('lands.index'))
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            description = request.form.get('description')
            region = request.form.get('region')
            city = request.form.get('city')
            district = request.form.get('district')
            address = request.form.get('address')
            latitude = float(request.form.get('latitude'))
            longitude = float(request.form.get('longitude'))
            area = float(request.form.get('area'))
            land_type = request.form.get('land_type')
            status = request.form.get('status')
            annual_return = float(request.form.get('annual_return', 0))
            occupancy_rate = float(request.form.get('occupancy_rate', 0))
            water_usage = float(request.form.get('water_usage', 0))
            yearly_income = float(request.form.get('yearly_income', 0))
            
            # Create new land
            land = Land(
                name=name,
                description=description,
                region=region,
                city=city,
                district=district,
                address=address,
                latitude=latitude,
                longitude=longitude,
                area=area,
                land_type=land_type,
                status=status,
                annual_return=annual_return,
                occupancy_rate=occupancy_rate,
                water_usage=water_usage,
                yearly_income=yearly_income
            )
            
            # Handle GeoJSON data if provided
            geom = request.form.get('geom')
            if geom:
                land.geom = geom
            
            db.session.add(land)
            db.session.commit()
            
            flash('تمت إضافة الأرض الوقفية بنجاح', 'success')
            return redirect(url_for('lands.view', land_id=land.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'خطأ عند إضافة الأرض: {str(e)}', 'danger')
    
    return render_template('lands/add.html')

@lands.route('/<int:land_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(land_id):
    """Edit an existing endowment land"""
    if not current_user.is_admin():
        flash('غير مسموح لك بتنفيذ هذه الإجراء', 'danger')
        return redirect(url_for('lands.view', land_id=land_id))
    
    land = Land.query.get_or_404(land_id)
    
    if request.method == 'POST':
        try:
            # Update land data
            land.name = request.form.get('name')
            land.description = request.form.get('description')
            land.region = request.form.get('region')
            land.city = request.form.get('city')
            land.district = request.form.get('district')
            land.address = request.form.get('address')
            land.latitude = float(request.form.get('latitude'))
            land.longitude = float(request.form.get('longitude'))
            land.area = float(request.form.get('area'))
            land.land_type = request.form.get('land_type')
            land.status = request.form.get('status')
            land.annual_return = float(request.form.get('annual_return', 0))
            land.occupancy_rate = float(request.form.get('occupancy_rate', 0))
            land.water_usage = float(request.form.get('water_usage', 0))
            land.yearly_income = float(request.form.get('yearly_income', 0))
            
            # Handle GeoJSON data if provided
            geom = request.form.get('geom')
            if geom:
                land.geom = geom
            
            land.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash('تم تحديث الأرض الوقفية بنجاح', 'success')
            return redirect(url_for('lands.view', land_id=land.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'خطأ عند تحديث الأرض: {str(e)}', 'danger')
    
    return render_template('lands/edit.html', land=land)

@lands.route('/<int:land_id>/delete', methods=['POST'])
@login_required
def delete(land_id):
    """Delete an endowment land"""
    if not current_user.is_admin():
        flash('غير مسموح لك بتنفيذ هذه الإجراء', 'danger')
        return redirect(url_for('lands.view', land_id=land_id))
    
    land = Land.query.get_or_404(land_id)
    
    try:
        # Delete related records first
        Report.query.filter_by(land_id=land_id).delete()
        Recommendation.query.filter_by(land_id=land_id).delete()
        Statistic.query.filter_by(land_id=land_id).delete()
        
        # Delete the land
        db.session.delete(land)
        db.session.commit()
        
        flash('تم حذف الأرض الوقفية بنجاح', 'success')
        return redirect(url_for('lands.index'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'خطأ عند حذف الأرض: {str(e)}', 'danger')
        return redirect(url_for('lands.view', land_id=land_id))

# API endpoints for the interactive map
@lands.route('/api/lands')
def api_lands():
    """API endpoint for lands GeoJSON data"""
    # Get filter parameters
    region = request.args.get('region')
    land_type = request.args.get('type')
    status = request.args.get('status')
    
    # Build query
    query = Land.query
    
    if region and region.strip():
        query = query.filter_by(region=region)
    if land_type and land_type.strip():
        query = query.filter_by(land_type=land_type)
    if status and status.strip():
        query = query.filter_by(status=status)
    
    # Get lands
    lands = query.all()
    
    # Debug log
    print(f"Found {len(lands)} lands matching the filter criteria")
    
    # Prepare GeoJSON data
    features = []
    for land in lands:
        # Debug log
        print(f"Land {land.id} status: {land.status}")
        
        # Ensure status is one of the expected values
        normalized_status = land.status
        if normalized_status not in ['available', 'invested', 'under_development']:
            print(f"Unexpected status value: {normalized_status}, defaulting to 'available'")
            normalized_status = 'available'
        
        # Create popup content
        popup_content = f"""
        <div class='map-popup'>
            <h5>{land.name}</h5>
            <p><strong>المنطقة:</strong> {land.region}</p>
            <p><strong>المدينة:</strong> {land.city}</p>
            <p><strong>المساحة:</strong> {'{:,}'.format(land.area)} م²</p>
            <p><strong>النوع:</strong> {land.land_type}</p>
            <p><strong>الحالة:</strong> 
                {'متاحة للاستثمار' if normalized_status == 'available' else 'قيد الاستثمار' if normalized_status == 'invested' else 'قيد التطوير' if normalized_status == 'under_development' else normalized_status}
            </p>
            <a href='{url_for('lands.view', land_id=land.id)}' class='btn btn-sm btn-primary'>عرض التفاصيل</a>
        </div>
        """
        
        # Create GeoJSON feature
        feature = {
            "type": "Feature",
            "properties": {
                "id": land.id,
                "name": land.name,
                "status": normalized_status,
                "type": land.land_type,
                "region": land.region,
                "city": land.city,
                "area": land.area,
                "popup_content": popup_content
            },
            "geometry": {
                "type": "Point",
                "coordinates": [land.longitude, land.latitude]
            }
        }
        features.append(feature)
    
    # Create GeoJSON object
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    # Debug log
    print(f"Returning GeoJSON with {len(features)} features")
    
    return jsonify(geojson)

def ensure_demo_data():
    """Ensure all demo data exists"""
    # Check if we have any lands in the database
    lands_count = Land.query.count()
    
    # If no lands exist, add all demo data
    if lands_count == 0:
        add_demo_lands()
        add_demo_recommendations()
        add_demo_reports()
        add_demo_statistics()
        return True
    
    # Check if we have recommendations, reports, and statistics
    recommendations_count = Recommendation.query.count()
    reports_count = Report.query.count()
    statistics_count = Statistic.query.count()
    
    # If any of these are missing, add them
    if recommendations_count == 0:
        add_demo_recommendations()
    if reports_count == 0:
        add_demo_reports()
    if statistics_count == 0:
        add_demo_statistics()
    
    return True

def add_demo_lands():
    """Add demo lands data to the database"""
    # Saudi Arabia regions with coordinates
    demo_lands = [
        # Riyadh Region
        {
            'name': 'أرض وقفية الرياض 1',
            'description': 'أرض وقفية في شمال الرياض مخصصة للمشاريع السكنية',
            'region': 'الرياض',
            'city': 'الرياض',
            'district': 'حي النرجس',
            'address': 'طريق الملك سلمان، حي النرجس، الرياض',
            'latitude': 24.7136,
            'longitude': 46.6753,
            'area': 5000,
            'land_type': 'سكني',
            'status': 'available',
            'annual_return': 8.5,
            'occupancy_rate': 0,
            'water_usage': 0,
            'yearly_income': 0
        },
        {
            'name': 'أرض وقفية الرياض 2',
            'description': 'أرض وقفية في وسط الرياض مخصصة للمشاريع التجارية',
            'region': 'الرياض',
            'city': 'الرياض',
            'district': 'حي العليا',
            'address': 'طريق العليا، حي العليا، الرياض',
            'latitude': 24.6911,
            'longitude': 46.6892,
            'area': 3500,
            'land_type': 'تجاري',
            'status': 'invested',
            'annual_return': 12.3,
            'occupancy_rate': 85,
            'water_usage': 450,
            'yearly_income': 750000
        },
        {
            'name': 'أرض وقفية الخرج',
            'description': 'أرض وقفية في الخرج مخصصة للمشاريع الزراعية',
            'region': 'الرياض',
            'city': 'الخرج',
            'district': 'حي الياسمين',
            'address': 'طريق الملك عبدالله، الخرج',
            'latitude': 24.1500,
            'longitude': 47.3000,
            'area': 15000,
            'land_type': 'زراعي',
            'status': 'under_development',
            'annual_return': 7.2,
            'occupancy_rate': 30,
            'water_usage': 2500,
            'yearly_income': 320000
        },
        
        # Makkah Region
        {
            'name': 'أرض وقفية جدة 1',
            'description': 'أرض وقفية في شمال جدة مخصصة للمشاريع السكنية والتجارية',
            'region': 'مكة المكرمة',
            'city': 'جدة',
            'district': 'حي الشاطئ',
            'address': 'طريق الكورنيش، حي الشاطئ، جدة',
            'latitude': 21.5433,
            'longitude': 39.1728,
            'area': 7500,
            'land_type': 'مختلط',
            'status': 'under_development',
            'annual_return': 10.8,
            'occupancy_rate': 40,
            'water_usage': 320,
            'yearly_income': 450000
        },
        {
            'name': 'أرض وقفية جدة 2',
            'description': 'أرض وقفية في وسط جدة مخصصة للمشاريع التعليمية',
            'region': 'مكة المكرمة',
            'city': 'جدة',
            'district': 'حي الروضة',
            'address': 'طريق المدينة، حي الروضة، جدة',
            'latitude': 21.4858,
            'longitude': 39.2134,
            'area': 4200,
            'land_type': 'تعليمي',
            'status': 'invested',
            'annual_return': 9.1,
            'occupancy_rate': 95,
            'water_usage': 280,
            'yearly_income': 520000
        },
        {
            'name': 'أرض وقفية مكة 1',
            'description': 'أرض وقفية في مكة المكرمة مخصصة للمشاريع السكنية',
            'region': 'مكة المكرمة',
            'city': 'مكة المكرمة',
            'district': 'العزيزية',
            'address': 'حي العزيزية، مكة المكرمة',
            'latitude': 21.3891,
            'longitude': 39.8579,
            'area': 4200,
            'land_type': 'سكني',
            'status': 'available',
            'annual_return': 9.2,
            'occupancy_rate': 0,
            'water_usage': 0,
            'yearly_income': 0
        },
        {
            'name': 'أرض وقفية الطائف',
            'description': 'أرض وقفية في الطائف مخصصة للمشاريع السياحية',
            'region': 'مكة المكرمة',
            'city': 'الطائف',
            'district': 'الشفا',
            'address': 'طريق الشفا، الطائف',
            'latitude': 21.2667,
            'longitude': 40.4167,
            'area': 9500,
            'land_type': 'سياحي',
            'status': 'invested',
            'annual_return': 14.2,
            'occupancy_rate': 75,
            'water_usage': 650,
            'yearly_income': 870000
        },
        
        # Madinah Region
        {
            'name': 'أرض وقفية المدينة 1',
            'description': 'أرض وقفية في المدينة المنورة مخصصة للمشاريع السكنية',
            'region': 'المدينة المنورة',
            'city': 'المدينة المنورة',
            'district': 'حي قباء',
            'address': 'طريق قباء، المدينة المنورة',
            'latitude': 24.4672,
            'longitude': 39.6151,
            'area': 3800,
            'land_type': 'سكني',
            'status': 'available',
            'annual_return': 7.8,
            'occupancy_rate': 0,
            'water_usage': 0,
            'yearly_income': 0
        },
        {
            'name': 'أرض وقفية ينبع',
            'description': 'أرض وقفية في ينبع مخصصة للمشاريع الصناعية',
            'region': 'المدينة المنورة',
            'city': 'ينبع',
            'district': 'ينبع الصناعية',
            'address': 'المنطقة الصناعية، ينبع',
            'latitude': 24.0231,
            'longitude': 38.1899,
            'area': 12000,
            'land_type': 'صناعي',
            'status': 'invested',
            'annual_return': 11.5,
            'occupancy_rate': 90,
            'water_usage': 1800,
            'yearly_income': 1250000
        },
        
        # Eastern Region
        {
            'name': 'أرض وقفية الدمام 1',
            'description': 'أرض وقفية في الدمام مخصصة للمشاريع التجارية',
            'region': 'المنطقة الشرقية',
            'city': 'الدمام',
            'district': 'حي الشاطئ',
            'address': 'طريق الخليج، حي الشاطئ، الدمام',
            'latitude': 26.4207,
            'longitude': 50.0888,
            'area': 6200,
            'land_type': 'تجاري',
            'status': 'invested',
            'annual_return': 11.5,
            'occupancy_rate': 92,
            'water_usage': 580,
            'yearly_income': 920000
        },
        {
            'name': 'أرض وقفية الخبر',
            'description': 'أرض وقفية في الخبر مخصصة للمشاريع السكنية',
            'region': 'المنطقة الشرقية',
            'city': 'الخبر',
            'district': 'حي الراكة',
            'address': 'طريق الظهران، حي الراكة، الخبر',
            'latitude': 26.2172,
            'longitude': 50.1971,
            'area': 4800,
            'land_type': 'سكني',
            'status': 'under_development',
            'annual_return': 9.7,
            'occupancy_rate': 35,
            'water_usage': 280,
            'yearly_income': 320000
        },
        {
            'name': 'أرض وقفية الجبيل',
            'description': 'أرض وقفية في الجبيل مخصصة للمشاريع الصناعية',
            'region': 'المنطقة الشرقية',
            'city': 'الجبيل',
            'district': 'الجبيل الصناعية',
            'address': 'المنطقة الصناعية، الجبيل',
            'latitude': 27.0174,
            'longitude': 49.5906,
            'area': 18000,
            'land_type': 'صناعي',
            'status': 'invested',
            'annual_return': 13.8,
            'occupancy_rate': 95,
            'water_usage': 2200,
            'yearly_income': 1850000
        },
        
        # Asir Region
        {
            'name': 'أرض وقفية أبها',
            'description': 'أرض وقفية في أبها مخصصة للمشاريع السياحية',
            'region': 'عسير',
            'city': 'أبها',
            'district': 'حي السد',
            'address': 'طريق الملك فهد، حي السد، أبها',
            'latitude': 18.2164,
            'longitude': 42.5053,
            'area': 8500,
            'land_type': 'سياحي',
            'status': 'available',
            'annual_return': 13.2,
            'occupancy_rate': 0,
            'water_usage': 0,
            'yearly_income': 0
        },
        {
            'name': 'أرض وقفية خميس مشيط',
            'description': 'أرض وقفية في خميس مشيط مخصصة للمشاريع التجارية',
            'region': 'عسير',
            'city': 'خميس مشيط',
            'district': 'وسط المدينة',
            'address': 'طريق الملك خالد، خميس مشيط',
            'latitude': 18.3078,
            'longitude': 42.7662,
            'area': 5200,
            'land_type': 'تجاري',
            'status': 'under_development',
            'annual_return': 10.5,
            'occupancy_rate': 45,
            'water_usage': 350,
            'yearly_income': 480000
        },
        
        # Qassim Region
        {
            'name': 'أرض وقفية بريدة',
            'description': 'أرض وقفية في بريدة مخصصة للمشاريع التعليمية',
            'region': 'القصيم',
            'city': 'بريدة',
            'district': 'حي الإسكان',
            'address': 'طريق الملك عبدالله، حي الإسكان، بريدة',
            'latitude': 26.3292,
            'longitude': 43.7667,
            'area': 5500,
            'land_type': 'تعليمي',
            'status': 'under_development',
            'annual_return': 7.5,
            'occupancy_rate': 60,
            'water_usage': 420,
            'yearly_income': 380000
        },
        {
            'name': 'أرض وقفية عنيزة',
            'description': 'أرض وقفية في عنيزة مخصصة للمشاريع الزراعية',
            'region': 'القصيم',
            'city': 'عنيزة',
            'district': 'المنطقة الزراعية',
            'address': 'طريق الملك سعود، عنيزة',
            'latitude': 26.0957,
            'longitude': 43.9930,
            'area': 22000,
            'land_type': 'زراعي',
            'status': 'invested',
            'annual_return': 8.3,
            'occupancy_rate': 100,
            'water_usage': 4500,
            'yearly_income': 720000
        },
        
        # Tabuk Region
        {
            'name': 'أرض وقفية تبوك',
            'description': 'أرض وقفية في تبوك مخصصة للمشاريع الزراعية',
            'region': 'تبوك',
            'city': 'تبوك',
            'district': 'حي المروج',
            'address': 'المنطقة الزراعية، تبوك',
            'latitude': 28.3998,
            'longitude': 36.5715,
            'area': 12000,
            'land_type': 'زراعي',
            'status': 'invested',
            'annual_return': 8.9,
            'occupancy_rate': 100,
            'water_usage': 1500,
            'yearly_income': 650000
        },
        
        # Northern Borders Region
        {
            'name': 'أرض وقفية عرعر',
            'description': 'أرض وقفية في عرعر مخصصة للمشاريع السكنية',
            'region': 'الحدود الشمالية',
            'city': 'عرعر',
            'district': 'وسط المدينة',
            'address': 'طريق الملك عبدالعزيز، عرعر',
            'latitude': 30.9753,
            'longitude': 41.0153,
            'area': 3800,
            'land_type': 'سكني',
            'status': 'available',
            'annual_return': 6.8,
            'occupancy_rate': 0,
            'water_usage': 0,
            'yearly_income': 0
        }
    ]
    
    for land_data in demo_lands:
        land = Land(**land_data)
        db.session.add(land)
    
    try:
        db.session.commit()
        print("Added demo lands to the database")
    except Exception as e:
        db.session.rollback()
        print(f"Error adding demo lands: {e}")

def add_demo_recommendations():
    """Add demo recommendations for lands"""
    # First check if we already have recommendations
    if Recommendation.query.first():
        print("Recommendations already exist, skipping demo data creation")
        return
    
    # Get an admin user or create one if none exists
    admin_user = User.query.filter_by(role='admin').first()
    if not admin_user:
        admin_user = User(username='admin', email='admin@wasaq.sa', 
                          password='adminpass', role='admin',
                          first_name='مدير', last_name='النظام')
        db.session.add(admin_user)
        db.session.commit()
    
    # Get all lands
    lands = Land.query.all()
    
    # Recommendation types in Arabic
    recommendation_types = ['تطوير', 'استثمار', 'صيانة', 'تأجير', 'بيع', 'شراكة']
    priorities = ['high', 'medium', 'low']
    statuses = ['pending', 'approved', 'rejected', 'implemented']
    
    for land in lands:
        # Number of recommendations per land (1-3)
        num_recommendations = random.randint(1, 3)
        
        for i in range(num_recommendations):
            # Generate random data for each recommendation
            rec_type = random.choice(recommendation_types)
            priority = random.choice(priorities)
            status = random.choice(statuses)
            
            # Create title and description based on land type and recommendation type
            if rec_type == 'تطوير':
                title = f"مقترح تطوير {land.land_type} في {land.city}"
                description = f"يقترح تطوير الأرض الوقفية في {land.district}، {land.city} لتحسين العائد السنوي وزيادة قيمة الأصول. يتضمن المشروع إنشاء مباني {land.land_type} حديثة تتناسب مع احتياجات المنطقة."
            elif rec_type == 'استثمار':
                title = f"فرصة استثمارية في {land.city}"
                description = f"تمثل هذه الأرض فرصة استثمارية ممتازة في قطاع {land.land_type}. يمكن تحقيق عوائد مجزية من خلال الشراكة مع مستثمرين متخصصين في هذا المجال."
            elif rec_type == 'صيانة':
                title = f"خطة صيانة للأرض في {land.district}"
                description = f"تحتاج الأرض إلى أعمال صيانة وتحسين للبنية التحتية لزيادة جاذبيتها للمستثمرين. تشمل الخطة تحسين شبكات المياه والكهرباء والطرق المحيطة."
            elif rec_type == 'تأجير':
                title = f"مقترح تأجير الأرض في {land.city}"
                description = f"يمكن تحقيق دخل ثابت من خلال تأجير الأرض لمستثمرين في قطاع {land.land_type} بعقود طويلة الأجل تضمن استقرار العائد."
            elif rec_type == 'بيع':
                title = f"دراسة جدوى بيع الأرض في {land.district}"
                description = f"في حال كانت الأرض غير مجدية للاستثمار طويل الأجل، يمكن دراسة إمكانية بيعها والاستفادة من قيمتها في شراء أصول أكثر جدوى."
            else:  # شراكة
                title = f"مقترح شراكة استراتيجية في {land.city}"
                description = f"يمكن تحقيق أقصى استفادة من الأرض من خلال شراكة استراتيجية مع مطورين متخصصين في قطاع {land.land_type}، مما يقلل المخاطر ويزيد العوائد."
            
            # Generate realistic financial data based on land area and type
            base_cost = land.area * random.uniform(500, 2000)
            if land.land_type == 'سكني':
                cost_multiplier = random.uniform(1.0, 1.5)
                return_multiplier = random.uniform(0.08, 0.12)
            elif land.land_type == 'تجاري':
                cost_multiplier = random.uniform(1.5, 2.5)
                return_multiplier = random.uniform(0.1, 0.18)
            elif land.land_type == 'صناعي':
                cost_multiplier = random.uniform(1.2, 2.0)
                return_multiplier = random.uniform(0.09, 0.15)
            elif land.land_type == 'زراعي':
                cost_multiplier = random.uniform(0.5, 1.0)
                return_multiplier = random.uniform(0.06, 0.1)
            else:  # مختلط، تعليمي، سياحي
                cost_multiplier = random.uniform(1.0, 2.0)
                return_multiplier = random.uniform(0.08, 0.14)
            
            estimated_cost = base_cost * cost_multiplier
            estimated_return = return_multiplier * 100  # Convert to percentage
            estimated_timeframe = random.randint(6, 36)  # 6 months to 3 years
            
            # Create the recommendation
            recommendation = Recommendation(
                title=title,
                description=description,
                recommendation_type=rec_type,
                priority=priority,
                status=status,
                confidence_score=random.uniform(0.65, 0.95),
                estimated_cost=estimated_cost,
                estimated_return=estimated_return,
                estimated_timeframe=estimated_timeframe,
                land_id=land.id,
                user_id=admin_user.id,
                supporting_data=json.dumps({
                    'market_analysis': 'تم تحليل السوق المحلي وتقييم الطلب',
                    'roi_calculation': f'تم حساب العائد على الاستثمار بناءً على معدل {estimated_return:.1f}%',
                    'risk_assessment': 'تم تقييم المخاطر المحتملة وخطط التخفيف'
                }),
                ai_model_version='v1.0'
            )
            
            db.session.add(recommendation)
    
    try:
        db.session.commit()
        print("Added demo recommendations to the database")
    except Exception as e:
        db.session.rollback()
        print(f"Error adding demo recommendations: {e}")

def add_demo_reports():
    """Add demo reports for lands"""
    # First check if we already have reports
    if Report.query.first():
        print("Reports already exist, skipping demo data creation")
        return
    
    # Get an admin user or create one if none exists
    admin_user = User.query.filter_by(role='admin').first()
    if not admin_user:
        admin_user = User(username='admin', email='admin@wasaq.sa', 
                          password='adminpass', role='admin',
                          first_name='مدير', last_name='النظام')
        db.session.add(admin_user)
        db.session.commit()
    
    # Get all lands
    lands = Land.query.all()
    
    # Report types in Arabic
    report_types = ['status', 'project_update', 'maintenance', 'inspection', 'financial']
    statuses = ['draft', 'published', 'archived']
    
    for land in lands:
        # Number of reports per land (1-4)
        num_reports = random.randint(1, 4)
        
        for i in range(num_reports):
            # Generate random data for each report
            report_type = random.choice(report_types)
            status = random.choice(statuses)
            
            # Create title and content based on land type and report type
            if report_type == 'status':
                title = f"تقرير حالة الأرض في {land.district}، {land.city}"
                content = f"""<h3>تقرير حالة الأرض الوقفية</h3>
                <p>تم إجراء زيارة ميدانية للأرض الوقفية الواقعة في {land.district}، {land.city} بتاريخ {datetime.now().strftime('%Y-%m-%d')}.</p>
                
                <h4>الحالة العامة</h4>
                <p>الأرض في حالة {['جيدة', 'ممتازة', 'متوسطة', 'تحتاج إلى تحسين'][random.randint(0, 3)]}. {['تم تسوير الأرض بالكامل', 'الأرض غير مسورة', 'تم تسوير جزء من الأرض'][random.randint(0, 2)]}.</p>
                
                <h4>البنية التحتية</h4>
                <p>توفر خدمات الكهرباء: {['متوفرة', 'غير متوفرة', 'متوفرة جزئياً'][random.randint(0, 2)]}</p>
                <p>توفر خدمات المياه: {['متوفرة', 'غير متوفرة', 'متوفرة جزئياً'][random.randint(0, 2)]}</p>
                <p>توفر خدمات الصرف الصحي: {['متوفرة', 'غير متوفرة', 'متوفرة جزئياً'][random.randint(0, 2)]}</p>
                
                <h4>الوضع القانوني</h4>
                <p>جميع الوثائق والصكوك سليمة ومحدثة.</p>
                
                <h4>التوصيات</h4>
                <p>{['يوصى بالاستثمار في هذه الأرض نظراً لموقعها الاستراتيجي', 'يوصى بإجراء صيانة دورية للأرض', 'يوصى بتطوير البنية التحتية للأرض لزيادة قيمتها'][random.randint(0, 2)]}</p>
                """
            elif report_type == 'project_update':
                title = f"تحديث مشروع {land.land_type} في {land.city}"
                content = f"""<h3>تحديث مشروع الأرض الوقفية</h3>
                <p>فيما يلي آخر التحديثات للمشروع المقام على الأرض الوقفية في {land.district}، {land.city}:</p>
                
                <h4>نسبة الإنجاز</h4>
                <p>بلغت نسبة الإنجاز في المشروع {random.randint(10, 95)}% حتى تاريخ {datetime.now().strftime('%Y-%m-%d')}.</p>
                
                <h4>الأعمال المنجزة</h4>
                <ul>
                    <li>تم الانتهاء من أعمال الحفر والأساسات</li>
                    <li>تم الانتهاء من {random.randint(20, 80)}% من الهيكل الإنشائي</li>
                    <li>جاري العمل على {['التشطيبات الداخلية', 'الواجهات الخارجية', 'أعمال الكهرباء والسباكة'][random.randint(0, 2)]}</li>
                </ul>
                
                <h4>التحديات</h4>
                <p>{['تأخر في توريد بعض المواد', 'ظروف جوية أثرت على سير العمل', 'لا توجد تحديات كبيرة، المشروع يسير وفق الخطة'][random.randint(0, 2)]}</p>
                
                <h4>الخطوات القادمة</h4>
                <p>من المتوقع الانتهاء من المشروع بحلول {datetime.now().replace(year=datetime.now().year + 1).strftime('%Y-%m-%d')}.</p>
                """
            elif report_type == 'maintenance':
                title = f"تقرير صيانة الأرض في {land.city}"
                content = f"""<h3>تقرير أعمال الصيانة</h3>
                <p>تم إجراء أعمال صيانة للأرض الوقفية في {land.district}، {land.city} خلال الفترة من {(datetime.now().replace(month=datetime.now().month-1) if datetime.now().month > 1 else datetime.now().replace(year=datetime.now().year-1, month=12)).strftime('%Y-%m-%d')} إلى {datetime.now().strftime('%Y-%m-%d')}.</p>
                
                <h4>الأعمال المنفذة</h4>
                <ul>
                    <li>{['صيانة السور المحيط بالأرض', 'تنظيف الأرض من المخلفات', 'إصلاح تسربات المياه'][random.randint(0, 2)]}</li>
                    <li>{['صيانة شبكة الكهرباء', 'صيانة شبكة المياه', 'صيانة شبكة الصرف الصحي'][random.randint(0, 2)]}</li>
                    <li>{['تسوية الأرض', 'إزالة الأعشاب الضارة', 'ترميم المباني القائمة'][random.randint(0, 2)]}</li>
                </ul>
                
                <h4>التكلفة الإجمالية</h4>
                <p>{'{:,.0f}'.format(random.uniform(10000, 100000))} ريال سعودي</p>
                
                <h4>التوصيات المستقبلية</h4>
                <p>يوصى بإجراء صيانة دورية كل {random.randint(3, 12)} أشهر للحفاظ على الأرض في حالة جيدة.</p>
                """
            elif report_type == 'inspection':
                title = f"تقرير تفتيش الأرض في {land.district}"
                content = f"""<h3>تقرير التفتيش الدوري</h3>
                <p>تم إجراء تفتيش دوري للأرض الوقفية في {land.district}، {land.city} بتاريخ {datetime.now().strftime('%Y-%m-%d')}.</p>
                
                <h4>نتائج التفتيش</h4>
                <p>الحالة العامة: {['ممتازة', 'جيدة', 'متوسطة', 'تحتاج إلى اهتمام'][random.randint(0, 3)]}</p>
                <p>الالتزام بشروط العقد: {['ملتزم تماماً', 'ملتزم بشكل جزئي', 'غير ملتزم'][random.randint(0, 2)]}</p>
                <p>المخالفات المرصودة: {['لا توجد مخالفات', 'توجد بعض المخالفات البسيطة', 'توجد مخالفات تحتاج إلى معالجة فورية'][random.randint(0, 2)]}</p>
                
                <h4>الإجراءات المتخذة</h4>
                <p>{['تم توجيه إنذار للمستثمر لمعالجة المخالفات', 'تم الاتفاق على خطة لتحسين الوضع', 'لا حاجة لاتخاذ إجراءات'][random.randint(0, 2)]}</p>
                
                <h4>الزيارة القادمة</h4>
                <p>من المقرر إجراء زيارة تفتيشية قادمة بتاريخ {datetime.now().replace(month=(datetime.now().month+3) % 12 or 12).strftime('%Y-%m-%d')}</p>
                """
            else:  # financial
                title = f"التقرير المالي للأرض في {land.city}"
                content = f"""<h3>التقرير المالي للأرض الوقفية</h3>
                <p>فيما يلي التقرير المالي للأرض الوقفية في {land.district}، {land.city} للفترة المنتهية في {datetime.now().strftime('%Y-%m-%d')}.</p>
                
                <h4>الإيرادات</h4>
                <p>إجمالي الإيرادات: {'{:,.0f}'.format(land.yearly_income if land.yearly_income > 0 else random.uniform(100000, 1000000))} ريال سعودي</p>
                <p>نسبة النمو: {'{:.1f}'.format(random.uniform(-5, 15))}% مقارنة بالفترة السابقة</p>
                
                <h4>المصروفات</h4>
                <p>تكاليف الصيانة: {'{:,.0f}'.format(random.uniform(10000, 100000))} ريال سعودي</p>
                <p>تكاليف الإدارة: {'{:,.0f}'.format(random.uniform(5000, 50000))} ريال سعودي</p>
                <p>مصروفات أخرى: {'{:,.0f}'.format(random.uniform(1000, 20000))} ريال سعودي</p>
                
                <h4>صافي الدخل</h4>
                <p>{'{:,.0f}'.format(land.yearly_income * 0.7 if land.yearly_income > 0 else random.uniform(50000, 800000))} ريال سعودي</p>
                
                <h4>العائد على الاستثمار</h4>
                <p>{'{:.1f}'.format(land.annual_return if land.annual_return > 0 else random.uniform(5, 15))}%</p>
                """
            
            # Create the report
            report = Report(
                title=title,
                content=content,
                report_type=report_type,
                status=status,
                land_id=land.id,
                user_id=admin_user.id,
                published_at=datetime.now() if status == 'published' else None,
                attachments=json.dumps([
                    {'name': 'صور الأرض.pdf', 'url': '#'},
                    {'name': 'مخططات.dwg', 'url': '#'}
                ]),
                tags=','.join([land.region, land.city, land.land_type])
            )
            
            db.session.add(report)
    
    try:
        db.session.commit()
        print("Added demo reports to the database")
    except Exception as e:
        db.session.rollback()
        print(f"Error adding demo reports: {e}")

def add_demo_statistics():
    """Add demo statistics for lands"""
    # First check if we already have statistics
    if Statistic.query.first():
        print("Statistics already exist, skipping demo data creation")
        return
    
    # Get all lands
    lands = Land.query.all()
    
    # Statistic categories
    categories = ['financial', 'usage', 'demographic']
    
    for land in lands:
        # Financial statistics
        financial_stats = [
            {
                'name': 'العائد السنوي',
                'description': 'متوسط العائد السنوي للأرض',
                'value': land.annual_return,
                'unit': 'percentage',
                'time_period': 'yearly'
            },
            {
                'name': 'الدخل السنوي',
                'description': 'متوسط الدخل السنوي من الأرض',
                'value': land.yearly_income,
                'unit': 'SAR',
                'time_period': 'yearly'
            },
            {
                'name': 'قيمة الأرض التقديرية',
                'description': 'القيمة السوقية التقديرية للأرض',
                'value': land.area * random.uniform(2000, 5000),
                'unit': 'SAR',
                'time_period': 'current'
            },
            {
                'name': 'تكاليف الصيانة',
                'description': 'متوسط تكاليف الصيانة السنوية',
                'value': land.area * random.uniform(50, 150),
                'unit': 'SAR',
                'time_period': 'yearly'
            }
        ]
        
        # Usage statistics
        usage_stats = [
            {
                'name': 'معدل الإشغال',
                'description': 'نسبة الإشغال الحالية للأرض',
                'value': land.occupancy_rate,
                'unit': 'percentage',
                'time_period': 'current'
            },
            {
                'name': 'استهلاك المياه',
                'description': 'متوسط استهلاك المياه الشهري',
                'value': land.water_usage,
                'unit': 'cubic_meters',
                'time_period': 'monthly'
            },
            {
                'name': 'استهلاك الكهرباء',
                'description': 'متوسط استهلاك الكهرباء الشهري',
                'value': land.area * random.uniform(0.5, 2.0),
                'unit': 'kWh',
                'time_period': 'monthly'
            },
            {
                'name': 'كفاءة استخدام المساحة',
                'description': 'نسبة استغلال مساحة الأرض',
                'value': random.uniform(60, 95),
                'unit': 'percentage',
                'time_period': 'current'
            }
        ]
        
        # Demographic statistics (for lands with occupants)
        demographic_stats = []
        if land.occupancy_rate > 0:
            demographic_stats = [
                {
                    'name': 'عدد المستفيدين',
                    'description': 'عدد الأشخاص المستفيدين من الأرض',
                    'value': int(land.area / 50) * (land.occupancy_rate / 100),
                    'unit': 'count',
                    'time_period': 'current'
                },
                {
                    'name': 'متوسط العمر',
                    'description': 'متوسط عمر المستفيدين',
                    'value': random.uniform(25, 45),
                    'unit': 'years',
                    'time_period': 'current'
                },
                {
                    'name': 'نسبة الرضا',
                    'description': 'نسبة رضا المستفيدين عن الخدمات',
                    'value': random.uniform(70, 95),
                    'unit': 'percentage',
                    'time_period': 'quarterly'
                }
            ]
        
        # Add all statistics to the database
        all_stats = [
            {'category': 'financial', 'stats': financial_stats},
            {'category': 'usage', 'stats': usage_stats},
            {'category': 'demographic', 'stats': demographic_stats}
        ]
        
        for stat_group in all_stats:
            category = stat_group['category']
            stats = stat_group['stats']
            
            for stat_data in stats:
                statistic = Statistic(
                    name=stat_data['name'],
                    description=stat_data['description'],
                    category=category,
                    value=stat_data['value'],
                    unit=stat_data['unit'],
                    time_period=stat_data['time_period'],
                    land_id=land.id,
                    data_source='نظام إدارة الأراضي الوقفية',
                    raw_data=json.dumps({
                        'historical_data': [
                            {'date': (datetime.now().replace(month=datetime.now().month-3) if datetime.now().month > 3 else datetime.now().replace(year=datetime.now().year-1, month=12-(3-datetime.now().month))).strftime('%Y-%m-%d'), 'value': stat_data['value'] * random.uniform(0.85, 0.95)},
                            {'date': (datetime.now().replace(month=datetime.now().month-2) if datetime.now().month > 2 else datetime.now().replace(year=datetime.now().year-1, month=12-(2-datetime.now().month))).strftime('%Y-%m-%d'), 'value': stat_data['value'] * random.uniform(0.9, 1.0)},
                            {'date': (datetime.now().replace(month=datetime.now().month-1) if datetime.now().month > 1 else datetime.now().replace(year=datetime.now().year-1, month=12)).strftime('%Y-%m-%d'), 'value': stat_data['value'] * random.uniform(0.95, 1.05)}
                        ],
                        'metadata': {
                            'collection_method': 'آلي',
                            'margin_of_error': random.uniform(1, 5)
                        }
                    })
                )
                db.session.add(statistic)
    
    try:
        db.session.commit()
        print("Added demo statistics to the database")
    except Exception as e:
        db.session.rollback()
        print(f"Error adding demo statistics: {e}")
