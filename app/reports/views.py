from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from . import reports
from app.models.report import Report
from app.models.land import Land
from app import db
from datetime import datetime, timedelta
import json
import os
import tempfile
from werkzeug.utils import secure_filename

@reports.route('/')
@login_required
def index():
    """List all reports"""
    # Get filter parameters
    report_type = request.args.get('type')
    status = request.args.get('status')
    land_id = request.args.get('land_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    page = request.args.get('page', 1, type=int)
    
    # Build query
    query = Report.query
    
    if report_type:
        query = query.filter_by(report_type=report_type)
    if status:
        query = query.filter_by(status=status)
    if land_id:
        query = query.filter_by(land_id=land_id)
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Report.created_at >= start_date_obj)
        except ValueError:
            pass
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Report.created_at <= end_date_obj)
        except ValueError:
            pass
    
    # Get reports with pagination
    reports_per_page = current_app.config.get('REPORTS_PER_PAGE', 10)
    reports_pagination = query.order_by(Report.created_at.desc()).paginate(page=page, per_page=reports_per_page, error_out=False)
    reports_list = reports_pagination.items
    
    # Get all lands for the filter dropdown
    lands = Land.query.all()
    
    # Get unique report types and statuses for filter dropdowns
    report_types = db.session.query(Report.report_type).distinct().all()
    statuses = db.session.query(Report.status).distinct().all()
    
    # Prepare data for charts
    # 1. Reports by Type
    type_counts = {}
    for r_type in report_types:
        if r_type[0]:  # Ensure not None
            count = Report.query.filter_by(report_type=r_type[0]).count()
            type_counts[r_type[0]] = count
    
    report_type_labels = list(type_counts.keys())
    report_type_data = list(type_counts.values())
    
    # 2. Reports by Region
    region_counts = {}
    regions = db.session.query(Land.region).distinct().all()
    for region in regions:
        if region[0]:  # Ensure not None
            # Count reports for lands in this region
            land_ids = [land.id for land in Land.query.filter_by(region=region[0]).all()]
            count = Report.query.filter(Report.land_id.in_(land_ids)).count() if land_ids else 0
            region_counts[region[0]] = count
    
    report_region_labels = list(region_counts.keys())
    report_region_data = list(region_counts.values())
    
    # 3. Reports Timeline
    # Get reports by month for the last 6 months
    timeline_labels = []
    timeline_data = []
    
    current_date = datetime.now()
    for i in range(5, -1, -1):  # Last 6 months
        # Calculate month date range
        month = (current_date.month - i) % 12
        if month == 0:
            month = 12
        year = current_date.year
        if current_date.month - i <= 0:
            year -= 1
        
        # Create date objects for start and end of month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        # Format month name
        month_name = start_date.strftime('%B %Y')
        timeline_labels.append(month_name)
        
        # Count reports in this month
        count = Report.query.filter(Report.created_at >= start_date, Report.created_at <= end_date).count()
        timeline_data.append(count)
    
    # Get Arabic translations for UI elements
    title_ar = "التقارير"
    page_header_ar = "تقارير الأراضي الوقفية"
    add_report_button_ar = "إضافة تقرير جديد"
    recent_reports_title_ar = "قائمة التقارير"
    report_title_column_ar = "عنوان التقرير"
    report_type_column_ar = "نوع التقرير"
    report_status_column_ar = "الحالة"
    report_land_column_ar = "الأرض"
    report_date_column_ar = "التاريخ"
    report_actions_column_ar = "إجراءات"
    no_reports_found_ar = "لم يتم العثور على تقارير"
    no_reports_found_message_ar = "لم يتم العثور على أي تقارير تطابق معايير البحث الخاصة بك."
    export_button_ar = "تصدير"
    reports_by_type_chart_title_ar = "التقارير حسب النوع"
    reports_by_region_chart_title_ar = "التقارير حسب المنطقة"
    reports_timeline_chart_title_ar = "توزيع التقارير على مدار الوقت"
    
    return render_template(
        'dashboard/reports.html',
        reports=reports_list,
        pagination=reports_pagination,
        lands=lands,
        report_types=[t[0] for t in report_types if t[0]],
        statuses=[s[0] for s in statuses if s[0]],
        selected_type=report_type,
        selected_status=status,
        selected_land_id=land_id,
        start_date=start_date,
        end_date=end_date,
        title_ar=title_ar,
        page_header_ar=page_header_ar,
        add_report_button_ar=add_report_button_ar,
        recent_reports_title_ar=recent_reports_title_ar,
        report_title_column_ar=report_title_column_ar,
        report_type_column_ar=report_type_column_ar,
        report_status_column_ar=report_status_column_ar,
        report_land_column_ar=report_land_column_ar,
        report_date_column_ar=report_date_column_ar,
        report_actions_column_ar=report_actions_column_ar,
        no_reports_found_ar=no_reports_found_ar,
        no_reports_found_message_ar=no_reports_found_message_ar,
        export_button_ar=export_button_ar,
        reports_by_type_chart_title_ar=reports_by_type_chart_title_ar,
        reports_by_region_chart_title_ar=reports_by_region_chart_title_ar,
        reports_timeline_chart_title_ar=reports_timeline_chart_title_ar,
        # Chart data
        report_type_labels=report_type_labels,
        report_type_data=report_type_data,
        report_region_labels=report_region_labels,
        report_region_data=report_region_data,
        report_timeline_labels=timeline_labels,
        report_timeline_data=timeline_data
    )

@reports.route('/<int:report_id>')
@login_required
def view(report_id):
    """View a specific report"""
    report = Report.query.get_or_404(report_id)
    
    # Parse attachments JSON if exists
    attachments = []
    if report.attachments:
        try:
            attachments = json.loads(report.attachments)
        except json.JSONDecodeError:
            attachments = []
    
    return render_template('reports/view.html', report=report, attachments=attachments)

@reports.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a new report"""
    if request.method == 'POST':
        try:
            # Get form data
            title = request.form.get('title')
            content = request.form.get('content')
            report_type = request.form.get('report_type')
            status = request.form.get('status', 'draft')
            land_id = request.form.get('land_id')
            tags = request.form.get('tags')
            
            # Validate required fields
            if not title or not content or not report_type or not land_id:
                flash('يرجى ملء جميع الحقول المطلوبة', 'danger')
                lands = Land.query.all()
                return render_template('dashboard/report_form.html', 
                                     lands=lands, 
                                     action="add",
                                     title_ar="إضافة تقرير جديد",
                                     form_title_label_ar="عنوان التقرير",
                                     form_content_label_ar="محتوى التقرير",
                                     form_type_label_ar="نوع التقرير",
                                     form_status_label_ar="حالة التقرير",
                                     form_land_label_ar="الأرض المرتبطة",
                                     form_tags_label_ar="الوسوم",
                                     form_attachments_label_ar="المرفقات",
                                     form_submit_button_ar="حفظ التقرير",
                                     form_cancel_button_ar="إلغاء")
            
            # Create new report
            new_report = Report(
                title=title,
                content=content,
                report_type=report_type,
                status=status,
                land_id=land_id,
                user_id=current_user.id,
                tags=tags
            )
            
            # Set published_at if status is published
            if status == 'published':
                new_report.published_at = datetime.now()
            
            # Handle file uploads
            files = request.files.getlist('attachments')
            attachments = []
            
            for file in files:
                if file and file.filename:
                    # Save file to uploads directory
                    filename = secure_filename(file.filename)
                    upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'reports')
                    os.makedirs(upload_dir, exist_ok=True)
                    file_path = os.path.join(upload_dir, filename)
                    file.save(file_path)
                    
                    # Add to attachments list
                    attachments.append({
                        'filename': filename,
                        'path': file_path,
                        'type': file.content_type
                    })
            
            # Save attachments as JSON
            if attachments:
                new_report.attachments = json.dumps(attachments)
            
            # Save to database
            db.session.add(new_report)
            db.session.commit()
            
            flash('تم إضافة التقرير بنجاح', 'success')
            return redirect(url_for('reports.view', report_id=new_report.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء إضافة التقرير: {str(e)}', 'danger')
    
    # GET request - show form
    lands = Land.query.all()
    
    # Arabic translations for form elements
    title_ar = "إضافة تقرير جديد"
    form_title_label_ar = "عنوان التقرير"
    form_content_label_ar = "محتوى التقرير"
    form_type_label_ar = "نوع التقرير"
    form_status_label_ar = "حالة التقرير"
    form_land_label_ar = "الأرض المرتبطة"
    form_tags_label_ar = "الوسوم"
    form_attachments_label_ar = "المرفقات"
    form_submit_button_ar = "حفظ التقرير"
    form_cancel_button_ar = "إلغاء"
    
    return render_template(
        'dashboard/report_form.html', 
        lands=lands, 
        action="add",
        title_ar=title_ar,
        form_title_label_ar=form_title_label_ar,
        form_content_label_ar=form_content_label_ar,
        form_type_label_ar=form_type_label_ar,
        form_status_label_ar=form_status_label_ar,
        form_land_label_ar=form_land_label_ar,
        form_tags_label_ar=form_tags_label_ar,
        form_attachments_label_ar=form_attachments_label_ar,
        form_submit_button_ar=form_submit_button_ar,
        form_cancel_button_ar=form_cancel_button_ar
    )

@reports.route('/<int:report_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(report_id):
    """Edit an existing report"""
    report = Report.query.get_or_404(report_id)
    
    # Check if user is author or admin
    if report.user_id != current_user.id and not current_user.is_admin():
        flash('غير مسموح لك بتعديل هذا التقرير', 'danger')
        return redirect(url_for('reports.view', report_id=report_id))
    
    # Parse existing attachments
    existing_attachments = []
    if report.attachments:
        try:
            existing_attachments = json.loads(report.attachments)
        except json.JSONDecodeError:
            existing_attachments = []
    
    if request.method == 'POST':
        try:
            # Update report data
            report.title = request.form.get('title')
            report.content = request.form.get('content')
            report.report_type = request.form.get('report_type')
            
            # Check if status is changing to published
            new_status = request.form.get('status', 'draft')
            if new_status == 'published' and report.status != 'published':
                report.published_at = datetime.utcnow()
            report.status = new_status
            
            report.land_id = request.form.get('land_id')
            report.tags = request.form.get('tags')
            
            # Handle file uploads
            attachments = existing_attachments.copy()
            if 'attachments' in request.files:
                files = request.files.getlist('attachments')
                for file in files:
                    if file and file.filename:
                        # Save file to uploads directory
                        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
                        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'reports')
                        os.makedirs(upload_folder, exist_ok=True)
                        file_path = os.path.join(upload_folder, filename)
                        file.save(file_path)
                        
                        # Add to attachments list
                        attachments.append({
                            'filename': filename,
                            'original_name': file.filename,
                            'path': f"/static/uploads/reports/{filename}"
                        })
            
            # Handle attachment deletions
            attachments_to_keep = request.form.getlist('keep_attachment')
            attachments = [a for a in attachments if a['filename'] in attachments_to_keep]
            
            report.attachments = json.dumps(attachments) if attachments else None
            report.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('تم تحديث التقرير بنجاح', 'success')
            return redirect(url_for('reports.view', report_id=report.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء تحديث التقرير: {str(e)}', 'danger')
    
    # Get all lands for the dropdown
    lands = Land.query.all()
    
    return render_template(
        'reports/edit.html', 
        report=report, 
        lands=lands, 
        attachments=existing_attachments
    )

@reports.route('/<int:report_id>/delete', methods=['POST'])
@login_required
def delete(report_id):
    """Delete a report"""
    report = Report.query.get_or_404(report_id)
    
    # Check if user is author or admin
    if report.user_id != current_user.id and not current_user.is_admin():
        flash('غير مسموح لك بحذف هذا التقرير', 'danger')
        return redirect(url_for('reports.view', report_id=report_id))
    
    try:
        # Delete the report
        db.session.delete(report)
        db.session.commit()
        
        flash('تم حذف التقرير بنجاح', 'success')
        return redirect(url_for('reports.index'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء حذف التقرير: {str(e)}', 'danger')
        return redirect(url_for('reports.view', report_id=report_id))

@reports.route('/<int:report_id>/download')
@login_required
def download_report(report_id):
    """Download a report as PDF"""
    report = Report.query.get_or_404(report_id)
    
    try:
        # In a real application, you would generate a PDF here
        # For now, we'll just create a simple text file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
            temp_file.write(f"Title: {report.title}\n\n".encode('utf-8'))
            temp_file.write(f"Type: {report.report_type}\n".encode('utf-8'))
            temp_file.write(f"Status: {report.status}\n".encode('utf-8'))
            temp_file.write(f"Date: {report.created_at}\n\n".encode('utf-8'))
            temp_file.write(f"Content:\n{report.content}".encode('utf-8'))
            temp_file_path = temp_file.name
        
        return send_file(
            temp_file_path,
            as_attachment=True,
            download_name=f"report_{report_id}_{datetime.now().strftime('%Y%m%d')}.txt",
            mimetype='text/plain'
        )
    
    except Exception as e:
        flash(f'حدث خطأ أثناء تنزيل التقرير: {str(e)}', 'danger')
        return redirect(url_for('reports.view', report_id=report_id))

@reports.route('/export')
@login_required
def export_reports():
    """Export filtered reports"""
    # Get filter parameters (same as index)
    report_type = request.args.get('type')
    status = request.args.get('status')
    land_id = request.args.get('land_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    export_format = request.args.get('format', 'csv')  # Default to CSV if not specified
    
    # Build query
    query = Report.query
    
    if report_type:
        query = query.filter_by(report_type=report_type)
    if status:
        query = query.filter_by(status=status)
    if land_id:
        query = query.filter_by(land_id=land_id)
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Report.created_at >= start_date_obj)
        except ValueError:
            pass
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Report.created_at <= end_date_obj)
        except ValueError:
            pass
    
    # Get reports
    reports_list = query.order_by(Report.created_at.desc()).all()
    
    try:
        # Handle different export formats
        if export_format == 'csv':
            # Create CSV file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
                # Write header
                header = "ID,Title,Type,Status,Land,Created,Published\n"
                temp_file.write(header.encode('utf-8'))
                
                # Write data
                for report in reports_list:
                    land_name = report.land.name if report.land else 'N/A'
                    published = report.published_at.strftime('%Y-%m-%d') if report.published_at else 'N/A'
                    
                    line = f"{report.id},\"{report.title}\",{report.report_type},{report.status},\"{land_name}\",{report.created_at.strftime('%Y-%m-%d')},{published}\n"
                    temp_file.write(line.encode('utf-8'))
                
                temp_file_path = temp_file.name
            
            return send_file(
                temp_file_path,
                as_attachment=True,
                download_name=f"reports_export_{datetime.now().strftime('%Y%m%d')}.csv",
                mimetype='text/csv'
            )
        
        elif export_format == 'excel':
            # For now, just return CSV as Excel is not implemented yet
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
                # Write header
                header = "ID,Title,Type,Status,Land,Created,Published\n"
                temp_file.write(header.encode('utf-8'))
                
                # Write data
                for report in reports_list:
                    land_name = report.land.name if report.land else 'N/A'
                    published = report.published_at.strftime('%Y-%m-%d') if report.published_at else 'N/A'
                    
                    line = f"{report.id},\"{report.title}\",{report.report_type},{report.status},\"{land_name}\",{report.created_at.strftime('%Y-%m-%d')},{published}\n"
                    temp_file.write(line.encode('utf-8'))
                
                temp_file_path = temp_file.name
            
            return send_file(
                temp_file_path,
                as_attachment=True,
                download_name=f"reports_export_{datetime.now().strftime('%Y%m%d')}.csv",
                mimetype='text/csv'
            )
        
        elif export_format == 'pdf':
            # Create a simple text file for now (PDF generation would require additional libraries)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
                temp_file.write(f"Reports Export - {datetime.now().strftime('%Y-%m-%d')}\n\n".encode('utf-8'))
                
                for report in reports_list:
                    land_name = report.land.name if report.land else 'N/A'
                    published = report.published_at.strftime('%Y-%m-%d') if report.published_at else 'N/A'
                    
                    temp_file.write(f"ID: {report.id}\n".encode('utf-8'))
                    temp_file.write(f"Title: {report.title}\n".encode('utf-8'))
                    temp_file.write(f"Type: {report.report_type}\n".encode('utf-8'))
                    temp_file.write(f"Status: {report.status}\n".encode('utf-8'))
                    temp_file.write(f"Land: {land_name}\n".encode('utf-8'))
                    temp_file.write(f"Created: {report.created_at.strftime('%Y-%m-%d')}\n".encode('utf-8'))
                    temp_file.write(f"Published: {published}\n\n".encode('utf-8'))
                
                temp_file_path = temp_file.name
            
            return send_file(
                temp_file_path,
                as_attachment=True,
                download_name=f"reports_export_{datetime.now().strftime('%Y%m%d')}.txt",
                mimetype='text/plain'
            )
        
        else:
            # Default to CSV for unknown formats
            flash('تنسيق التصدير غير مدعوم. تم التصدير بتنسيق CSV.', 'warning')
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
                # Write header
                header = "ID,Title,Type,Status,Land,Created,Published\n"
                temp_file.write(header.encode('utf-8'))
                
                # Write data
                for report in reports_list:
                    land_name = report.land.name if report.land else 'N/A'
                    published = report.published_at.strftime('%Y-%m-%d') if report.published_at else 'N/A'
                    
                    line = f"{report.id},\"{report.title}\",{report.report_type},{report.status},\"{land_name}\",{report.created_at.strftime('%Y-%m-%d')},{published}\n"
                    temp_file.write(line.encode('utf-8'))
                
                temp_file_path = temp_file.name
            
            return send_file(
                temp_file_path,
                as_attachment=True,
                download_name=f"reports_export_{datetime.now().strftime('%Y%m%d')}.csv",
                mimetype='text/csv'
            )
    
    except Exception as e:
        flash(f'حدث خطأ أثناء تصدير التقارير: {str(e)}', 'danger')
        return redirect(url_for('reports.index'))
