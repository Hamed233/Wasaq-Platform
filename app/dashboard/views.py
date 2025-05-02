from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, make_response
from flask_login import login_required, current_user
from . import dashboard
from app.models.land import Land
from app.models.report import Report
from app.models.recommendation import Recommendation
from app.models.statistic import Statistic
from app import db
import os
import json
import random
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import csv
import xlsxwriter
import pdfkit

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
    regions = ['الرياض', 'مكة المكرمة', 'المدينة المنورة', 'القصيم', 'الشرقية', 'عسير', 'تبوك', 'حائل', 'الحدود الشمالية', 'جازان', 'نجران', 'الباحة', 'الجوف']
    region_stats = []
    
    for region in regions:
        lands_in_region = Land.query.filter_by(region=region).all()
        total_area = sum(land.area for land in lands_in_region if land.area)
        
        # Fix division by zero error
        lands_with_return = [land for land in lands_in_region if land.annual_return]
        avg_return = sum(land.annual_return for land in lands_with_return) / len(lands_with_return) if lands_with_return else 0
        
        region_stats.append({
            'name': region,  # Already in Arabic
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
    
    # Get summary statistics
    lands = Land.query.all()
    total_lands = len(lands)
    
    # Calculate total value (using area * average price per sqm as an approximation)
    total_value = sum(land.area * 1000 for land in lands if land.area) # Assuming 1000 SAR per sqm as default
    
    # Calculate average annual return
    lands_with_return = [land for land in lands if land.annual_return is not None]
    avg_return = sum(land.annual_return for land in lands_with_return) / len(lands_with_return) if lands_with_return else 0
    
    # Calculate average occupancy rate
    lands_with_occupancy = [land for land in lands if land.occupancy_rate is not None]
    avg_occupancy = sum(land.occupancy_rate for land in lands_with_occupancy) / len(lands_with_occupancy) if lands_with_occupancy else 0
    
    # Get regions and land types for filters
    regions = sorted(set(land.region for land in lands if land.region))
    land_types = sorted(set(land.land_type for land in lands if land.land_type))
    
    # Prepare data for region distribution chart
    region_counts = {}
    for land in lands:
        if land.region:
            region_counts[land.region] = region_counts.get(land.region, 0) + 1
    
    region_labels = list(region_counts.keys())
    region_data = list(region_counts.values())
    
    # Prepare data for land type distribution chart
    type_counts = {}
    for land in lands:
        if land.land_type:
            type_counts[land.land_type] = type_counts.get(land.land_type, 0) + 1
    
    type_labels = list(type_counts.keys())
    type_data = list(type_counts.values())
    
    # Prepare data for land status distribution chart
    status_counts = {}
    for land in lands:
        if land.status:
            status_counts[land.status] = status_counts.get(land.status, 0) + 1
    
    status_labels = list(status_counts.keys())
    status_data = list(status_counts.values())
    
    # Prepare data for annual return by region chart
    region_returns = {}
    region_counts_with_return = {}
    
    for land in lands:
        if land.region and land.annual_return is not None:
            if land.region not in region_returns:
                region_returns[land.region] = 0
                region_counts_with_return[land.region] = 0
            
            region_returns[land.region] += land.annual_return
            region_counts_with_return[land.region] += 1
    
    region_avg_returns = {}
    for region in region_returns:
        if region_counts_with_return[region] > 0:
            region_avg_returns[region] = region_returns[region] / region_counts_with_return[region]
    
    return_labels = list(region_avg_returns.keys())
    return_data = list(region_avg_returns.values())
    
    return render_template(
        'dashboard/statistics.html',
        period=period,
        financial_data=financial_data,
        usage_data=usage_data,
        demographic_data=demographic_data,
        total_lands=total_lands,
        total_value=total_value,
        avg_return=avg_return,
        avg_occupancy=avg_occupancy,
        regions=regions,
        land_types=land_types,
        region_labels=region_labels,
        region_data=region_data,
        type_labels=type_labels,
        type_data=type_data,
        status_labels=status_labels,
        status_data=status_data,
        return_labels=return_labels,
        return_data=return_data
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
    page = request.args.get('page', 1, type=int)
    per_page = 9  # 9 recommendations per page (3x3 grid)
    offset = (page - 1) * per_page
    pagination = query.order_by(Recommendation.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    recommendations = pagination.items
    
    # Calculate counts for status breakdown
    total_recommendations = len(recommendations)
    pending_count = sum(1 for rec in recommendations if rec.status == 'pending')
    approved_count = sum(1 for rec in recommendations if rec.status == 'approved')
    rejected_count = sum(1 for rec in recommendations if rec.status == 'rejected')
    implemented_count = sum(1 for rec in recommendations if rec.status == 'implemented')
    
    # Group recommendations by land
    lands_with_recommendations = {}
    for rec in recommendations:
        if rec.land_id not in lands_with_recommendations:
            lands_with_recommendations[rec.land_id] = {
                'land': rec.land,
                'recommendations': []
            }
        lands_with_recommendations[rec.land_id]['recommendations'].append(rec)
    
    # Calculate average expected return
    if recommendations:
        avg_expected_return = sum(rec.estimated_return or 0 for rec in recommendations) / len(recommendations) if recommendations else 0
    else:
        avg_expected_return = 0
    
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
        selected_type=rec_type,
        total_recommendations=total_recommendations,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        implemented_count=implemented_count,
        recommendations=recommendations,
        avg_expected_return=avg_expected_return,
        pagination=pagination
    )

@dashboard.route('/generate_recommendations')
@login_required
def generate_recommendations():
    """Generate AI recommendations for all lands"""
    # if not current_user.is_admin():
    #     flash('غير مسموح لك بتنفيذ هذا الإجراء', 'danger')
    #     return redirect(url_for('dashboard.recommendations'))
    
    # Get all lands
    lands = Land.query.all()
    
    try:
        # For demo purposes, we'll create recommendations without a trained model
        # by using our demo data generation function from lands module
        from app.lands.views import add_demo_data_for_land
        
        # Generate recommendations for each land
        recommendations_count = 0
        for land in lands:
            # Skip lands that already have recent recommendations
            recent_recommendations = Recommendation.query.filter_by(land_id=land.id).filter(
                Recommendation.created_at >= datetime.utcnow() - timedelta(days=30)
            ).count()
            
            if recent_recommendations > 0:
                continue
            
            # Generate demo recommendations for this land
            # Note: add_demo_data_for_land handles its own database session
            # so we don't need to commit here
            add_demo_data_for_land(land.id)
            recommendations_count += 3  # Typically adds 3 recommendations per land
        
        flash(f'تم إنشاء {recommendations_count} توصية جديدة بنجاح', 'success')
    except Exception as e:
        flash(f'حدث خطأ أثناء إنشاء التوصيات: {str(e)}', 'danger')
        current_app.logger.error(f"Error generating recommendations: {str(e)}")
    
    return redirect(url_for('dashboard.recommendations'))

@dashboard.route('/reports')
@login_required
def reports():
    """Dashboard reports page"""
    # Get filters from request
    report_type = request.args.get('type')
    status = request.args.get('status')
    region = request.args.get('region')
    
    # Build query
    query = Report.query
    
    if report_type:
        query = query.filter_by(report_type=report_type)
    if status:
        query = query.filter_by(status=status)
    if region:
        query = query.join(Land).filter(Land.region == region)
    
    # Get reports
    reports = query.order_by(Report.created_at.desc()).all()
    
    # Get filter options
    report_types = sorted(set(report.report_type for report in Report.query.all() if report.report_type))
    statuses = sorted(set(report.status for report in Report.query.all() if report.status))
    
    # Get regions from lands
    regions = sorted(set(land.region for land in Land.query.all() if land.region))
    
    # Arabic translations
    report_type_options_ar = {
        'status': 'تقرير حالة',
        'project_update': 'تحديث مشروع',
        'maintenance': 'صيانة',
        'inspection': 'تفتيش',
        'financial': 'مالي'
    }
    
    status_options_ar = {
        'draft': 'مسودة',
        'published': 'منشور',
        'archived': 'مؤرشف'
    }
    
    # Prepare chart data
    report_type_labels = [report_type_options_ar.get(t, t) for t in report_types]
    report_type_data = [Report.query.filter_by(report_type=t).count() for t in report_types]
    
    # Region data
    region_names_ar = {
        region: region for region in regions
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
    
    # Arabic UI text
    arabic_ui_text = {
        'title_ar': 'تقارير الأداء - وثاق',
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
    
    return render_template(
        'dashboard/reports.html',
        reports=reports,
        report_types=report_types,
        statuses=statuses,
        regions=regions,
        report_type_options_ar=report_type_options_ar,
        status_options_ar=status_options_ar,
        selected_type=report_type,
        selected_status=status,
        selected_region=region,
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
