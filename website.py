import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sqlalchemy import or_
from datetime import datetime
import logging
import traceback
from dotenv import load_dotenv

load_dotenv()

# Setup logging to see errors in the console/logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key_here')
db_url = os.getenv('DATABASE_URL', 'sqlite:///expense_tracker.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Models will be here or in a separate file
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('user', 'admin'), default='user')
    is_active_status = db.Column(db.Boolean, default=True) # Renamed to avoid confusion with is_active from UserMixin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_active(self):
        return self.is_active_status

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.Enum('income', 'expense'), default='expense')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expenses = db.relationship('Expense', backref='category', lazy=True)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    monthly_limit = db.Column(db.Numeric(10, 2), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    
    cat_rel = db.relationship('Category', backref='budgets', lazy=True)

@app.errorhandler(500)
def internal_error(error):
    logger.error("Internal Server Error (500) Triggered!")
    logger.error(traceback.format_exc())
    return render_template('500.html'), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_exists = User.query.filter((User.email == email) | (User.username == username)).first()
        if user_exists:
            flash('Email or Username already exists.', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password_hash=hashed_password, role='user')
        db.session.add(new_user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            if not user.is_active_status:
                flash('Your account has been deactivated. Please contact admin.', 'danger')
                return redirect(url_for('login'))
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            logout_user()
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email, role='admin').first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Admin Login Unsuccessful.', 'danger')
    return render_template('admin_login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Expenses for current month
    today = datetime.today()
    expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        db.extract('month', Expense.date) == today.month,
        db.extract('year', Expense.date) == today.year
    ).all()
    
    total_expenses = sum(e.amount for e in expenses)
    
    # Budget for current month
    budgets = Budget.query.filter(
        Budget.user_id == current_user.id,
        Budget.month == today.month,
        Budget.year == today.year
    ).all()
    
    total_budget = sum(b.monthly_limit for b in budgets)
    remaining_balance = total_budget - total_expenses
    
    # Check if any budgets are exceeded to notify user on dashboard
    for budget in budgets:
        spent = db.session.query(db.func.sum(Expense.amount)).filter(
            Expense.user_id == current_user.id,
            Expense.category_id == budget.category_id,
            db.extract('month', Expense.date) == today.month,
            db.extract('year', Expense.date) == today.year
        ).scalar() or 0
        
        if float(spent) > float(budget.monthly_limit):
             category = Category.query.get(budget.category_id)
             flash(f'Alert: You have crossed your {category.name} budget! (Limit: ₹{budget.monthly_limit:.2f}, Spent: ₹{spent:.2f})', 'budget_alert')
    
    # Recent Transactions
    recent_expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).limit(5).all()
    
    # Chart Data: Category-wise
    cat_stats = db.session.query(Category.name, db.func.sum(Expense.amount)).join(Expense).filter(
        Expense.user_id == current_user.id
    ).group_by(Category.name).all()
    
    category_data = {
        'labels': [c[0] for c in cat_stats],
        'values': [float(c[1]) for c in cat_stats]
    }
    
    # Chart Data: Trend (last 6 months - placeholder/simple version)
    trend_data = {
        'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        'values': [1200, 1900, 3000, 500, 2000, 3000] # Mock data for now
    }

    return render_template('dashboard.html', 
                           total_expenses=total_expenses, 
                           total_budget=total_budget,
                           remaining_balance=remaining_balance,
                           recent_expenses=recent_expenses,
                           category_data=category_data,
                           trend_data=trend_data)

def check_budget_exceeded(user_id, category_id, expense_date):
    budget = Budget.query.filter_by(
        user_id=user_id,
        category_id=int(category_id),
        month=expense_date.month,
        year=expense_date.year
    ).first()
    
    if budget:
        spent = db.session.query(db.func.sum(Expense.amount)).filter(
            Expense.user_id == user_id,
            Expense.category_id == int(category_id),
            db.extract('month', Expense.date) == expense_date.month,
            db.extract('year', Expense.date) == expense_date.year
        ).scalar() or 0
        
        if float(spent) > float(budget.monthly_limit):
             category = Category.query.get(int(category_id))
             if category:
                flash(f'Warning: You have exceeded your monthly budget of ₹{budget.monthly_limit:.2f} for {category.name}. Total spent: ₹{spent:.2f}!', 'budget_alert')


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Update user details
        if username:
            current_user.username = username
        if email:
            current_user.email = email
        if password:
            current_user.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
            
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
        
    return render_template('profile.html', user=current_user)

@app.route('/expense/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    categories = Category.query.filter((Category.user_id == None) | (Category.user_id == current_user.id)).all()
    if request.method == 'POST':
        # Check if they are adding a new category
        new_category_name = request.form.get('new_category')
        if new_category_name:
            # Check if category already exists for user
            existing = Category.query.filter(Category.name.ilike(new_category_name), (Category.user_id == None) | (Category.user_id == current_user.id)).first()
            if not existing:
                custom_cat = Category(name=new_category_name, user_id=current_user.id)
                db.session.add(custom_cat)
                db.session.commit()
                category_id = custom_cat.id
                flash('Custom category added!', 'success')
            else:
                category_id = existing.id
        else:
            category_id = request.form.get('category')
            
        amount = request.form.get('amount')
        description = request.form.get('description')
        date = request.form.get('date')
        
        new_expense = Expense(
            user_id=current_user.id,
            category_id=category_id,
            amount=amount,
            description=description,
            date=datetime.strptime(date, '%Y-%m-%d')
        )
        db.session.add(new_expense)
        db.session.commit()
        check_budget_exceeded(current_user.id, category_id, new_expense.date)
        flash('Expense added successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_expense.html', categories=categories, today_date=datetime.today().strftime('%Y-%m-%d'))

@app.route('/expenses')
@login_required
def expenses():
    category_id = request.args.get('category')
    month_str = request.args.get('month') # expected YYYY-MM
    
    query = Expense.query.filter_by(user_id=current_user.id)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    if month_str:
        year, month = map(int, month_str.split('-'))
        query = query.filter(db.extract('year', Expense.date) == year, db.extract('month', Expense.date) == month)
        
    all_expenses = query.order_by(Expense.date.desc()).all()
    categories = Category.query.filter((Category.user_id == None) | (Category.user_id == current_user.id)).all()
    return render_template('expenses.html', expenses=all_expenses, categories=categories)

@app.route('/expense/edit/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != current_user.id and current_user.role != 'admin':
        abort(403)
        
    categories = Category.query.filter((Category.user_id == None) | (Category.user_id == current_user.id)).all()
    if request.method == 'POST':
        expense.amount = request.form.get('amount')
        expense.category_id = request.form.get('category')
        expense.description = request.form.get('description')
        expense.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d')
        db.session.commit()
        check_budget_exceeded(current_user.id, expense.category_id, expense.date)
        flash('Expense updated!', 'success')
        return redirect(url_for('expenses'))
        
    return render_template('edit_expense.html', expense=expense, categories=categories)

@app.route('/expense/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != current_user.id and current_user.role != 'admin':
        abort(403)
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted.', 'info')
    return redirect(url_for('expenses'))

@app.route('/budgets', methods=['GET', 'POST'])
@login_required
def budgets():
    today = datetime.today()
    if request.method == 'POST':
        new_category_name = request.form.get('new_category')
        if new_category_name:
            existing = Category.query.filter(Category.name.ilike(new_category_name), (Category.user_id == None) | (Category.user_id == current_user.id)).first()
            if not existing:
                custom_cat = Category(name=new_category_name, user_id=current_user.id)
                db.session.add(custom_cat)
                db.session.commit()
                category_id = custom_cat.id
                flash('Custom category added for budget!', 'success')
            else:
                category_id = existing.id
        else:
            category_id = request.form.get('category')
            
        monthly_limit = request.form.get('limit')
        
        existing_budget = Budget.query.filter_by(
            user_id=current_user.id,
            category_id=category_id,
            month=today.month,
            year=today.year
        ).first()
        
        if existing_budget:
            existing_budget.monthly_limit = monthly_limit
        else:
            new_budget = Budget(
                user_id=current_user.id,
                category_id=category_id,
                monthly_limit=monthly_limit,
                month=today.month,
                year=today.year
            )
            db.session.add(new_budget)
            
        db.session.commit()
        flash('Budget updated successfully!', 'success')
        return redirect(url_for('budgets'))

    user_budgets = Budget.query.filter_by(
        user_id=current_user.id,
        month=today.month,
        year=today.year
    ).all()
    
    budget_list = []
    for b in user_budgets:
        spent = db.session.query(db.func.sum(Expense.amount)).filter(
            Expense.user_id == current_user.id,
            Expense.category_id == b.category_id,
            db.extract('month', Expense.date) == b.month,
            db.extract('year', Expense.date) == b.year
        ).scalar() or 0
        
        category = Category.query.get(b.category_id)
        budget_list.append({
            'category_name': category.name,
            'spent': float(spent),
            'limit': float(b.monthly_limit),
            'month_name': today.strftime('%B'),
            'year': b.year
        })
        
    categories = Category.query.filter((Category.user_id == None) | (Category.user_id == current_user.id)).all()
    return render_template('budgets.html', 
                           budgets=budget_list, 
                           categories=categories,
                           current_month=today.strftime('%Y-%m'))

from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    total_users = User.query.filter_by(role='user').count()
    total_expenses = db.session.query(db.func.sum(Expense.amount)).scalar() or 0
    total_categories = Category.query.count()
    
    return render_template('admin_dashboard.html', 
                           total_users=total_users,
                           total_expenses=float(total_expenses),
                           total_categories=total_categories)

@app.route('/admin/users')
@login_required
@admin_required
def manage_users():
    users = User.query.filter_by(role='user').all()
    return render_template('manage_users.html', users=users)

@app.route('/admin/user/toggle/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active_status = not user.is_active_status
    db.session.commit()
    status = "activated" if user.is_active_status else "deactivated"
    flash(f'User {user.username} has been {status}.', 'info')
    return redirect(url_for('manage_users'))

@app.route('/admin/expenses')
@login_required
@admin_required
def manage_expenses():
    all_expenses = Expense.query.order_by(Expense.date.desc()).all()
    return render_template('manage_expenses_admin.html', expenses=all_expenses)

@app.route('/admin/categories', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_categories():
    if request.method == 'POST':
        name = request.form.get('name')
        new_cat = Category(name=name, user_id=None)
        db.session.add(new_cat)
        db.session.commit()
        flash(f'Category {name} added.', 'success')
        return redirect(url_for('manage_categories'))
    categories = Category.query.filter(Category.user_id == None).all()
    return render_template('manage_categories.html', categories=categories)

@app.route('/export/<string:format>')
@login_required
def export_data(format):
    import pandas as pd
    from io import BytesIO, StringIO
    from flask import send_file
    
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    data = []
    for e in expenses:
        category = Category.query.get(e.category_id)
        data.append({
            'Date': e.date,
            'Category': category.name,
            'Amount': float(e.amount),
            'Description': e.description
        })
    df = pd.DataFrame(data)
    
    if format == 'csv':
        buffer = StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        return send_file(BytesIO(buffer.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='expenses.csv')
    
    elif format == 'excel':
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        return send_file(buffer, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='expenses.xlsx')

    flash('Export format not supported.', 'danger')
    return redirect(url_for('dashboard'))

# Database initialization
with app.app_context():
    try:
        db.create_all()
        # Create default categories if none exist
        if not Category.query.first():
            cats = ['Food', 'Travel', 'Education', 'Bills', 'Shopping', 'Health']
            for c in cats:
                db.session.add(Category(name=c))
            db.session.commit()
            logger.info("Default categories created.")
            
        # Create a default admin account
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            hashed_admin_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
            default_admin = User(username='AdminUser', email='admin@trackify.com', password_hash=hashed_admin_pw, role='admin')
            db.session.add(default_admin)
            db.session.commit()
            logger.info("Default admin created.")
    except Exception as e:
        logger.error("DB Initialization Error: " + str(e))
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    app.run(debug=True, port=5001)
