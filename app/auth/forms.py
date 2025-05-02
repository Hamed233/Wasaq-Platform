from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models.user import User

class LoginForm(FlaskForm):
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    remember_me = BooleanField('تذكرني')
    submit = SubmitField('تسجيل الدخول')

class RegistrationForm(FlaskForm):
    first_name = StringField('الاسم الأول', validators=[DataRequired(), Length(1, 64)])
    last_name = StringField('الاسم الأخير', validators=[DataRequired(), Length(1, 64)])
    username = StringField('اسم المستخدم', validators=[DataRequired(), Length(1, 64)])
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    password = PasswordField('كلمة المرور', validators=[DataRequired(), Length(min=8)])
    password_confirm = PasswordField('تأكيد كلمة المرور', validators=[DataRequired(), EqualTo('password')])
    terms = BooleanField('أوافق على شروط الاستخدام وسياسة الخصوصية', validators=[DataRequired()])
    submit = SubmitField('إنشاء الحساب')
    
    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('البريد الإلكتروني مستخدم بالفعل')
    
    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('اسم المستخدم مستخدم بالفعل')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('كلمة المرور الحالية', validators=[DataRequired()])
    password = PasswordField('كلمة المرور الجديدة', validators=[DataRequired(), Length(min=8)])
    password_confirm = PasswordField('تأكيد كلمة المرور الجديدة', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('تغيير كلمة المرور')

class ResetPasswordRequestForm(FlaskForm):
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    submit = SubmitField('إرسال تعليمات إعادة تعيين كلمة المرور')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('كلمة المرور الجديدة', validators=[DataRequired(), Length(min=8)])
    password_confirm = PasswordField('تأكيد كلمة المرور الجديدة', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('إعادة تعيين كلمة المرور')

class EditProfileForm(FlaskForm):
    first_name = StringField('الاسم الأول', validators=[DataRequired(), Length(1, 64)])
    last_name = StringField('الاسم الأخير', validators=[DataRequired(), Length(1, 64)])
    username = StringField('اسم المستخدم', validators=[DataRequired(), Length(1, 64)])
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    bio = TextAreaField('نبذة عني', validators=[Length(max=500)])
    submit = SubmitField('تحديث الملف الشخصي')
    
    def __init__(self, original_username, original_email, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email
    
    def validate_email(self, field):
        if field.data != self.original_email and User.query.filter_by(email=field.data).first():
            raise ValidationError('البريد الإلكتروني مستخدم بالفعل')
    
    def validate_username(self, field):
        if field.data != self.original_username and User.query.filter_by(username=field.data).first():
            raise ValidationError('اسم المستخدم مستخدم بالفعل')
