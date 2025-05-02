from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, make_response
from flask_login import login_required, current_user
from . import dashboard
from app.models.land import Land
from app.models.report import Report
from app.models.recommendation import Recommendation
from app.models.statistic import Statistic
from app import db
import json
from datetime import datetime, timedelta
import io
import csv
import xlsxwriter
import pdfkit
import os

@dashboard.route('/')
@login_required
def index():
    """Main dashboard page"""
    # Get summary statistics
    total_lands = Land.query.count()
    available_lands = Land.query.filter_by(status='available').count()
    invested_lands = Land.query.filter_by(status='invested').count()
    under_development = Land.query.filter_by(status='under_development').count()
    
    # Get recent reports
    recent_reports = Report.query.order_by(Report.created_at.desc()).limit(5).all()
    
    # Get top recommendations
    top_recommendations = Recommendation.query.filter_by(status='pending').order_by(
        Recommendation.priority.desc(), 
        Recommendation.confidence_score.desc()
    ).limit(5).all()
    
    # Get regional statistics
    regions = ['Northern', 'Southern', 'Eastern', 'Western', 'Central']
    region_names_ar = {
        'Northern': 'الشمالية',
        'Southern': 'الجنوبية',
        'Eastern': 'الشرقية',
        'Western': 'الغربية',
        'Central': 'الوسطى'
    }
    region_stats = []
    
    for region in regions:
        lands_in_region = Land.query.filter_by(region=region).all()
        total_area = sum(land.area for land in lands_in_region if land.area)
        
        # Fix division by zero error
        lands_with_return = [land for land in lands_in_region if land.annual_return]
        avg_return = sum(land.annual_return for land in lands_with_return) / len(lands_with_return) if lands_with_return else 0
        
        region_stats.append({
            'name': region_names_ar.get(region, region),  # Use Arabic name if available
            'count': len(lands_in_region),
            'total_area': total_area,
            'avg_return': avg_return
        })
    
    return render_template(
        'dashboard/index.html',
        total_lands=total_lands,
        available_lands=available_lands,
        invested_lands=invested_lands,
        under_development=under_development,
        recent_reports=recent_reports,
        top_recommendations=top_recommendations,
        region_stats=region_stats
    )

@dashboard.route('/statistics')
@login_required
def statistics():
    """Dashboard statistics page"""
    # Get time period from request (default to last 30 days)
    period = request.args.get('period', '30')
    try:
        days = int(period)
    except ValueError:
        days = 30
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get statistics for the time period
    stats = Statistic.query.filter(Statistic.recorded_at >= start_date).all()
    
    # Group statistics by category
    financial_stats = [s for s in stats if s.category == 'financial']
    usage_stats = [s for s in stats if s.category == 'usage']
    demographic_stats = [s for s in stats if s.category == 'demographic']
    
    # Prepare data for charts
    financial_data = prepare_chart_data(financial_stats)
    usage_data = prepare_chart_data(usage_stats)
    demographic_data = prepare_chart_data(demographic_stats)
    
    return render_template(
        'dashboard/statistics.html',
        period=period,
        financial_data=financial_data,
        usage_data=usage_data,
        demographic_data=demographic_data
    )

@dashboard.route('/export_statistics')
@login_required
def export_statistics():
    """Export statistics data"""
    format_type = request.args.get('format', 'csv')
    
    # Get statistics data
    stats = Statistic.query.all()
    
    if format_type == 'csv':
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Name', 'Category', 'Value', 'Land', 'Recorded At'])
        
        # Write data
        for stat in stats:
            land_name = stat.land.name if stat.land else 'N/A'
            writer.writerow([stat.id, stat.name, stat.category, stat.value, land_name, stat.recorded_at])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=statistics.csv"
        response.headers["Content-type"] = "text/csv"
        
        return response
    
    elif format_type == 'excel':
        # Create Excel file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()
        
        # Write header
        header_format = workbook.add_format({'bold': True})
        headers = ['ID', 'Name', 'Category', 'Value', 'Land', 'Recorded At']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write data
        for row, stat in enumerate(stats, 1):
            land_name = stat.land.name if stat.land else 'N/A'
            worksheet.write(row, 0, stat.id)
            worksheet.write(row, 1, stat.name)
            worksheet.write(row, 2, stat.category)
            worksheet.write(row, 3, stat.value)
            worksheet.write(row, 4, land_name)
            worksheet.write(row, 5, stat.recorded_at.strftime('%Y-%m-%d %H:%M:%S'))
        
        workbook.close()
        output.seek(0)
        
        # Create response
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=statistics.xlsx"
        response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        return response
    
    elif format_type == 'pdf':
        # Create PDF
        html = render_template(
            'dashboard/export_statistics.html',
            stats=stats,
            title='Statistics Export',
            date=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        # Convert HTML to PDF
        pdf = pdfkit.from_string(html, False)
        
        # Create response
        response = make_response(pdf)
        response.headers["Content-Disposition"] = "attachment; filename=statistics.pdf"
        response.headers["Content-type"] = "application/pdf"
        
        return response
    
    else:
        flash('Unsupported export format', 'danger')
        return redirect(url_for('dashboard.statistics'))

@dashboard.route('/recommendations')
@login_required
def recommendations():
    """Dashboard recommendations page"""
    # Get filter parameters
    priority = request.args.get('priority')
    status = request.args.get('status')
    rec_type = request.args.get('type')
    
    # Build query
    query = Recommendation.query
    
    if priority:
        query = query.filter_by(priority=priority)
    if status:
        query = query.filter_by(status=status)
    if rec_type:
        query = query.filter_by(recommendation_type=rec_type)
    
    # Get recommendations
    recommendations = query.order_by(Recommendation.created_at.desc()).all()
    
    # Group recommendations by land
    lands_with_recommendations = {}
    for rec in recommendations:
        if rec.land_id not in lands_with_recommendations:
            lands_with_recommendations[rec.land_id] = {
                'land': rec.land,
                'recommendations': []
            }
        lands_with_recommendations[rec.land_id]['recommendations'].append(rec)
    
    # Get filter options for dropdowns
    priority_options = ['high', 'medium', 'low']
    status_options = ['pending', 'approved', 'rejected', 'implemented']
    type_options = ['investment', 'development', 'maintenance', 'sale']
    
    # Arabic translations
    priority_options_ar = {
        'high': 'عالية',
        'medium': 'متوسطة',
        'low': 'منخفضة'
    }
    
    status_options_ar = {
        'pending': 'قيد الانظار',
        'approved': 'معتمدة',
        'rejected': 'مرفوضة',
        'implemented': 'منفذة'
    }
    
    type_options_ar = {
        'investment': 'استثمار',
        'development': 'تطوير',
        'maintenance': 'صيانة',
        'sale': 'بيع'
    }
    
    return render_template(
        'dashboard/recommendations.html',
        lands_with_recommendations=lands_with_recommendations,
        priority_options=priority_options,
        status_options=status_options,
        type_options=type_options,
        priority_options_ar=priority_options_ar,
        status_options_ar=status_options_ar,
        type_options_ar=type_options_ar,
        selected_priority=priority,
        selected_status=status,
        selected_type=rec_type
    )

@dashboard.route('/generate_recommendations')
@login_required
def generate_recommendations():
    """Generate AI recommendations for all lands"""
    if not current_user.is_admin():
        flash('غير مسموح لك بتنفيذ هذا الإجراء', 'danger')
        return redirect(url_for('dashboard.recommendations'))
    
    # Get all lands
    lands = Land.query.all()
    
    # Initialize recommendation model
    model_path = os.path.join(current_app.root_path, 'ai', 'models', 'recommendation_model.joblib')
    
    try:
        # Check if model exists, otherwise train a new one
        if os.path.exists(model_path):
            from app.ai.recommendation_model import RecommendationModel
            model = RecommendationModel(model_path=model_path)
        else:
            # For demo purposes, we'll create recommendations without a trained model
            from app.ai.recommendation_model import RecommendationModel
            model = RecommendationModel()
        
        # Generate recommendations for each land
        recommendations_count = 0
        for land in lands:
            # Skip lands that already have recent recommendations
            recent_recommendations = Recommendation.query.filter_by(land_id=land.id).filter(
                Recommendation.created_at >= datetime.utcnow() - timedelta(days=30)
            ).count()
            
            if recent_recommendations > 0:
                continue
            
            # Generate recommendations for this land
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
                recommendations_count += 1
        
        db.session.commit()
        flash(f'تم إنشاء {recommendations_count} توصية بنجاح', 'success')
    
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء إنشاء التوصيات: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard.recommendations'))

@dashboard.route('/reports')
@login_required
def reports():
    """Dashboard reports page"""
    # Get filter parameters
    report_type = request.args.get('type')
    status = request.args.get('status')
    land_id = request.args.get('land_id')
    page = request.args.get('page', 1, type=int)
    
    # Build query
    query = Report.query
    
    if report_type:
        query = query.filter_by(type=report_type)
    if status:
        query = query.filter_by(status=status)
    if land_id:
        query = query.filter_by(land_id=land_id)
    
    # Get reports with pagination
    pagination = query.order_by(Report.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    reports = pagination.items
    
    # Get filter options for dropdowns
    type_options = ['inspection', 'valuation', 'environmental', 'legal', 'financial']
    status_options = ['pending', 'approved', 'rejected', 'archived']
    
    # Arabic translations
    type_options_ar = {
        'inspection': 'تفتيش',
        'valuation': 'تقييم',
        'environmental': 'بيئي',
        'legal': 'قانوني',
        'financial': 'مالي'
    }
    
    status_options_ar = {
        'pending': 'قيد الانتظار',
        'approved': 'معتمد',
        'rejected': 'مرفوض',
        'archived': 'مؤرشف'
    }
    
    lands = Land.query.all()
    
    # Arabic UI text
    arabic_ui_text = {
        'title_ar': 'تقارير الأداء - وقاف',
        'page_header_ar': 'تقارير الأداء',
        'add_report_button_ar': 'إضافة تقرير جديد',
        'report_type_label_ar': 'نوع التقرير',
        'report_status_label_ar': 'الحالة',
        'land_label_ar': 'الأرض',
        'all_types_option_ar': 'جميع الأنواع',
        'all_statuses_option_ar': 'جميع الحالات',
        'all_lands_option_ar': 'جميع الأراضي',
        'apply_filter_button_ar': 'تطبيق التصفية',
        'reports_by_type_chart_title_ar': 'توزيع التقارير حسب النوع',
        'reports_by_region_chart_title_ar': 'توزيع التقارير حسب المنطقة',
        'reports_timeline_chart_title_ar': 'تطور التقارير عبر الزمن',
        'recent_reports_title_ar': 'أحدث التقارير',
        'export_button_ar': 'تصدير',
        'report_title_column_ar': 'العنوان',
        'report_type_column_ar': 'النوع',
        'report_status_column_ar': 'الحالة',
        'report_land_column_ar': 'الأرض',
        'report_author_column_ar': 'الكاتب',
        'report_date_column_ar': 'التاريخ',
        'report_actions_column_ar': 'الإجراءات',
        'attachment_tooltip_ar': 'يحتوي على مرفق',
        'report_type_status_ar': 'حالة',
        'report_type_project_update_ar': 'تحديث مشروع',
        'report_type_maintenance_ar': 'صيانة',
        'report_status_pending_ar': 'قيد الانتظار',
        'report_status_approved_ar': 'معتمد',
        'report_status_rejected_ar': 'مرفوض',
        'no_reports_found_ar': 'لم يتم العثور على تقارير',
        'no_reports_found_message_ar': 'لم يتم العثور على أي تقارير تطابق معايير البحث الخاصة بك.'
    }
    
    # Prepare chart data
    report_type_labels = [type_options_ar.get(t, t) for t in type_options]
    report_type_data = [Report.query.filter_by(type=t).count() for t in type_options]
    
    # Region data
    regions = ['Northern', 'Southern', 'Eastern', 'Western', 'Central']
    region_names_ar = {
        'Northern': 'الشمالية',
        'Southern': 'الجنوبية',
        'Eastern': 'الشرقية',
        'Western': 'الغربية',
        'Central': 'الوسطى'
    }
    report_region_labels = [region_names_ar.get(r, r) for r in regions]
    report_region_data = [Report.query.join(Land).filter(Land.region == r).count() for r in regions]
    
    # Timeline data
    from datetime import datetime, timedelta
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    timeline_labels = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(31)]
    timeline_data = [Report.query.filter(
        Report.created_at >= (start_date + timedelta(days=i)),
        Report.created_at < (start_date + timedelta(days=i+1))
    ).count() for i in range(31)]
    
    return render_template(
        'dashboard/reports.html',
        reports=reports,
        pagination=pagination,
        type_options=type_options,
        status_options=status_options,
        type_options_ar=type_options_ar,
        status_options_ar=status_options_ar,
        lands=lands,
        selected_type=report_type,
        selected_status=status,
        selected_land=land_id,
        report_type_labels=report_type_labels,
        report_type_data=report_type_data,
        report_region_labels=report_region_labels,
        report_region_data=report_region_data,
        timeline_labels=timeline_labels,
        timeline_data=timeline_data,
        **arabic_ui_text
    )

# Helper functions
def prepare_chart_data(stats):
    """Prepare statistics data for charts"""
    data = {
        'labels': [],
        'datasets': []
    }
    
    # Group by name and time period
    grouped_stats = {}
    for stat in stats:
        if stat.name not in grouped_stats:
            grouped_stats[stat.name] = []
        grouped_stats[stat.name].append({
            'value': stat.value,
            'recorded_at': stat.recorded_at,
            'unit': stat.unit
        })
    
    # Sort by recorded_at and prepare datasets
    for name, values in grouped_stats.items():
        sorted_values = sorted(values, key=lambda x: x['recorded_at'])
        
        dataset = {
            'label': name,
            'data': [v['value'] for v in sorted_values],
            'borderWidth': 1
        }
        
        data['datasets'].append(dataset)
        
        # Add labels (dates) if not already added
        if not data['labels'] and sorted_values:
            data['labels'] = [v['recorded_at'].strftime('%Y-%m-%d') for v in sorted_values]
    
    return json.dumps(data)
