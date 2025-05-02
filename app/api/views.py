from flask import jsonify, request, current_app, url_for
from flask_login import login_required, current_user
from . import api
from app.models.land import Land
from app.models.report import Report
from app.models.recommendation import Recommendation
from app.models.statistic import Statistic
from app import db
import json
from datetime import datetime
from functools import wraps
import jwt

# Authentication decorator for API endpoints
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check if token is in headers
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            # Decode token
            data = jwt.decode(
                token, 
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            
            # Get user from token data
            from app.models.user import User
            current_user = User.query.get(data['user_id'])
            
            if not current_user:
                return jsonify({'message': 'Invalid token'}), 401
            
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

# API endpoints
@api.route('/token', methods=['POST'])
def get_token():
    """Get authentication token"""
    auth = request.authorization
    
    if not auth or not auth.username or not auth.password:
        return jsonify({'message': 'Authentication required'}), 401
    
    # Verify credentials
    from app.models.user import User
    user = User.query.filter_by(email=auth.username).first()
    
    if not user or not user.verify_password(auth.password):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    # Generate token
    token = jwt.encode(
        {
            'user_id': user.id,
            'exp': datetime.utcnow() + current_app.config.get('JWT_EXPIRATION_DELTA', datetime.timedelta(hours=24))
        },
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )
    
    return jsonify({
        'token': token,
        'user_id': user.id,
        'username': user.username,
        'email': user.email
    })

@api.route('/lands', methods=['GET'])
@token_required
def get_lands(current_user):
    """Get all lands"""
    # Get filter parameters
    region = request.args.get('region')
    land_type = request.args.get('type')
    status = request.args.get('status')
    
    # Build query
    query = Land.query
    
    if region:
        query = query.filter_by(region=region)
    if land_type:
        query = query.filter_by(land_type=land_type)
    if status:
        query = query.filter_by(status=status)
    
    # Get lands
    lands = query.all()
    
    # Convert to JSON
    lands_data = [land.to_dict() for land in lands]
    
    return jsonify({
        'count': len(lands_data),
        'lands': lands_data
    })

@api.route('/lands/<int:land_id>', methods=['GET'])
@token_required
def get_land(current_user, land_id):
    """Get a specific land"""
    land = Land.query.get_or_404(land_id)
    
    return jsonify(land.to_dict())

@api.route('/lands/<int:land_id>/reports', methods=['GET'])
@token_required
def get_land_reports(current_user, land_id):
    """Get reports for a specific land"""
    land = Land.query.get_or_404(land_id)
    
    # Get reports
    reports = Report.query.filter_by(land_id=land_id).order_by(Report.created_at.desc()).all()
    
    # Convert to JSON
    reports_data = [report.to_dict() for report in reports]
    
    return jsonify({
        'count': len(reports_data),
        'land_id': land_id,
        'land_name': land.name,
        'reports': reports_data
    })

@api.route('/lands/<int:land_id>/recommendations', methods=['GET'])
@token_required
def get_land_recommendations(current_user, land_id):
    """Get recommendations for a specific land"""
    land = Land.query.get_or_404(land_id)
    
    # Get recommendations
    recommendations = Recommendation.query.filter_by(land_id=land_id).order_by(
        Recommendation.priority.desc(), 
        Recommendation.confidence_score.desc()
    ).all()
    
    # Convert to JSON
    recommendations_data = [rec.to_dict() for rec in recommendations]
    
    return jsonify({
        'count': len(recommendations_data),
        'land_id': land_id,
        'land_name': land.name,
        'recommendations': recommendations_data
    })

@api.route('/lands/<int:land_id>/statistics', methods=['GET'])
@token_required
def get_land_statistics(current_user, land_id):
    """Get statistics for a specific land"""
    land = Land.query.get_or_404(land_id)
    
    # Get statistics
    statistics = Statistic.query.filter_by(land_id=land_id).all()
    
    # Convert to JSON and group by category
    statistics_by_category = {}
    for stat in statistics:
        if stat.category not in statistics_by_category:
            statistics_by_category[stat.category] = []
        statistics_by_category[stat.category].append(stat.to_dict())
    
    return jsonify({
        'land_id': land_id,
        'land_name': land.name,
        'statistics': statistics_by_category
    })

@api.route('/reports', methods=['GET'])
@token_required
def get_reports(current_user):
    """Get all reports"""
    # Get filter parameters
    report_type = request.args.get('type')
    status = request.args.get('status')
    land_id = request.args.get('land_id')
    
    # Build query
    query = Report.query
    
    if report_type:
        query = query.filter_by(report_type=report_type)
    if status:
        query = query.filter_by(status=status)
    if land_id:
        query = query.filter_by(land_id=land_id)
    
    # Get reports
    reports = query.order_by(Report.created_at.desc()).all()
    
    # Convert to JSON
    reports_data = [report.to_dict() for report in reports]
    
    return jsonify({
        'count': len(reports_data),
        'reports': reports_data
    })

@api.route('/reports/<int:report_id>', methods=['GET'])
@token_required
def get_report(current_user, report_id):
    """Get a specific report"""
    report = Report.query.get_or_404(report_id)
    
    return jsonify(report.to_dict())

@api.route('/recommendations', methods=['GET'])
@token_required
def get_recommendations(current_user):
    """Get all recommendations"""
    # Get filter parameters
    rec_type = request.args.get('type')
    status = request.args.get('status')
    priority = request.args.get('priority')
    
    # Build query
    query = Recommendation.query
    
    if rec_type:
        query = query.filter_by(recommendation_type=rec_type)
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    
    # Get recommendations
    recommendations = query.order_by(
        Recommendation.priority.desc(), 
        Recommendation.confidence_score.desc()
    ).all()
    
    # Convert to JSON
    recommendations_data = [rec.to_dict() for rec in recommendations]
    
    return jsonify({
        'count': len(recommendations_data),
        'recommendations': recommendations_data
    })

@api.route('/recommendations/<int:recommendation_id>', methods=['GET'])
@token_required
def get_recommendation(current_user, recommendation_id):
    """Get a specific recommendation"""
    recommendation = Recommendation.query.get_or_404(recommendation_id)
    
    return jsonify(recommendation.to_dict())

@api.route('/statistics', methods=['GET'])
@token_required
def get_statistics(current_user):
    """Get all statistics"""
    # Get filter parameters
    category = request.args.get('category')
    
    # Build query
    query = Statistic.query
    
    if category:
        query = query.filter_by(category=category)
    
    # Get statistics
    statistics = query.all()
    
    # Convert to JSON and group by category
    statistics_by_category = {}
    for stat in statistics:
        if stat.category not in statistics_by_category:
            statistics_by_category[stat.category] = []
        statistics_by_category[stat.category].append(stat.to_dict())
    
    return jsonify({
        'statistics': statistics_by_category
    })

# Admin-only endpoints
@api.route('/lands', methods=['POST'])
@token_required
def create_land(current_user):
    """Create a new land (admin only)"""
    if not current_user.is_admin():
        return jsonify({'message': 'Permission denied'}), 403
    
    data = request.get_json()
    
    if not data or not all(k in data for k in ['name', 'latitude', 'longitude', 'region']):
        return jsonify({'message': 'Missing required fields'}), 400
    
    try:
        # Create new land
        land = Land(
            name=data['name'],
            description=data.get('description', ''),
            region=data['region'],
            city=data.get('city', ''),
            district=data.get('district', ''),
            address=data.get('address', ''),
            latitude=float(data['latitude']),
            longitude=float(data['longitude']),
            area=float(data.get('area', 0)),
            land_type=data.get('land_type', ''),
            status=data.get('status', 'available'),
            annual_return=float(data.get('annual_return', 0)),
            occupancy_rate=float(data.get('occupancy_rate', 0)),
            water_usage=float(data.get('water_usage', 0)),
            yearly_income=float(data.get('yearly_income', 0)),
            geom=json.dumps(data.get('geom', None)) if 'geom' in data else None
        )
        
        db.session.add(land)
        db.session.commit()
        
        return jsonify({
            'message': 'Land created successfully',
            'land': land.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating land: {str(e)}'}), 500

@api.route('/lands/<int:land_id>', methods=['PUT'])
@token_required
def update_land(current_user, land_id):
    """Update an existing land (admin only)"""
    if not current_user.is_admin():
        return jsonify({'message': 'Permission denied'}), 403
    
    land = Land.query.get_or_404(land_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'message': 'No data provided'}), 400
    
    try:
        # Update land fields
        if 'name' in data:
            land.name = data['name']
        if 'description' in data:
            land.description = data['description']
        if 'region' in data:
            land.region = data['region']
        if 'city' in data:
            land.city = data['city']
        if 'district' in data:
            land.district = data['district']
        if 'address' in data:
            land.address = data['address']
        if 'latitude' in data:
            land.latitude = float(data['latitude'])
        if 'longitude' in data:
            land.longitude = float(data['longitude'])
        if 'area' in data:
            land.area = float(data['area'])
        if 'land_type' in data:
            land.land_type = data['land_type']
        if 'status' in data:
            land.status = data['status']
        if 'annual_return' in data:
            land.annual_return = float(data['annual_return'])
        if 'occupancy_rate' in data:
            land.occupancy_rate = float(data['occupancy_rate'])
        if 'water_usage' in data:
            land.water_usage = float(data['water_usage'])
        if 'yearly_income' in data:
            land.yearly_income = float(data['yearly_income'])
        if 'geom' in data:
            land.geom = json.dumps(data['geom'])
        
        land.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Land updated successfully',
            'land': land.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating land: {str(e)}'}), 500

@api.route('/lands/<int:land_id>', methods=['DELETE'])
@token_required
def delete_land(current_user, land_id):
    """Delete a land (admin only)"""
    if not current_user.is_admin():
        return jsonify({'message': 'Permission denied'}), 403
    
    land = Land.query.get_or_404(land_id)
    
    try:
        # Delete related records first
        Report.query.filter_by(land_id=land_id).delete()
        Recommendation.query.filter_by(land_id=land_id).delete()
        Statistic.query.filter_by(land_id=land_id).delete()
        
        # Delete the land
        db.session.delete(land)
        db.session.commit()
        
        return jsonify({'message': 'Land deleted successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting land: {str(e)}'}), 500

@api.route('/reports', methods=['POST'])
@token_required
def create_report(current_user):
    """Create a new report"""
    data = request.get_json()
    
    if not data or not all(k in data for k in ['title', 'content', 'report_type', 'land_id']):
        return jsonify({'message': 'Missing required fields'}), 400
    
    try:
        # Create new report
        report = Report(
            title=data['title'],
            content=data['content'],
            report_type=data['report_type'],
            status=data.get('status', 'draft'),
            land_id=data['land_id'],
            user_id=current_user.id,
            tags=data.get('tags', ''),
            attachments=json.dumps(data.get('attachments', [])) if 'attachments' in data else None
        )
        
        # Set published_at if status is published
        if report.status == 'published':
            report.published_at = datetime.utcnow()
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'message': 'Report created successfully',
            'report': report.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating report: {str(e)}'}), 500

@api.route('/reports/<int:report_id>', methods=['PUT'])
@token_required
def update_report(current_user, report_id):
    """Update an existing report"""
    report = Report.query.get_or_404(report_id)
    
    # Check if user is author or admin
    if report.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'message': 'Permission denied'}), 403
    
    data = request.get_json()
    
    if not data:
        return jsonify({'message': 'No data provided'}), 400
    
    try:
        # Update report fields
        if 'title' in data:
            report.title = data['title']
        if 'content' in data:
            report.content = data['content']
        if 'report_type' in data:
            report.report_type = data['report_type']
        if 'tags' in data:
            report.tags = data['tags']
        if 'attachments' in data:
            report.attachments = json.dumps(data['attachments'])
        
        # Check if status is changing to published
        if 'status' in data and data['status'] == 'published' and report.status != 'published':
            report.published_at = datetime.utcnow()
        if 'status' in data:
            report.status = data['status']
        
        report.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Report updated successfully',
            'report': report.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating report: {str(e)}'}), 500

@api.route('/reports/<int:report_id>', methods=['DELETE'])
@token_required
def delete_report(current_user, report_id):
    """Delete a report"""
    report = Report.query.get_or_404(report_id)
    
    # Check if user is author or admin
    if report.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'message': 'Permission denied'}), 403
    
    try:
        # Delete the report
        db.session.delete(report)
        db.session.commit()
        
        return jsonify({'message': 'Report deleted successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting report: {str(e)}'}), 500
