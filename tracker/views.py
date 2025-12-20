import json
import csv
from datetime import datetime, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Transaction, Category, UserProfile
from .forms import (
    UserRegistrationForm, UserLoginForm, PasswordResetRequestForm,
    UserProfileForm
)


# Authentication Views
def welcome_view(request):
    """Welcome/Landing page"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'tracker/welcome.html')


def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    
    return render(request, 'tracker/login.html', {'form': form})


def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            
            # Use get_or_create to avoid IntegrityError
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            # If profile was just created, set default values
            if created:
                # Set default currency or other profile fields
                profile.currency = 'USD'  # or your default
                profile.save()
                
                # Create default categories for the new user
                create_default_categories(user)
                
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'tracker/register.html', {'form': form})


def forgot_password_view(request):
    """Password reset request"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            # In production, send actual email
            messages.info(request, 'Password reset link sent to your email (demo mode)')
            return redirect('login')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'tracker/forgot_password.html', {'form': form})


def logout_view(request):
    """User logout"""
    logout(request)
    messages.info(request, 'Logged out successfully')
    return redirect('welcome')

# Main Application Views
def get_user_profile(user):
    """Safely get or create user profile"""
    try:
        return UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return UserProfile.objects.create(user=user)

@login_required
def dashboard_view(request):
    """Dashboard/Financial Overview"""
    # Safely get user profile
    user_profile = get_user_profile(request.user)
    
    today = timezone.now().date()
    current_month = today.replace(day=1)
    current_year = today.year
    current_month_num = today.month
    
    # Get monthly summary
    monthly_transactions = Transaction.objects.filter(
        user=request.user,
        date__year=current_year,
        date__month=current_month_num
    )
    
    income = monthly_transactions.filter(transaction_type='income').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    
    expenses = monthly_transactions.filter(transaction_type='expense').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    
    balance = income - expenses
    savings_rate = (balance / income * 100) if income > 0 else 0
    
    # Category breakdown for pie chart
    category_data = {}
    category_expenses = monthly_transactions.filter(transaction_type='expense').values('category__name').annotate(
        total=Sum('amount')
    )
    
    for item in category_expenses:
        category_name = item['category__name'] or 'Uncategorized'
        category_data[category_name] = float(item['total'])
    
    # Monthly trend (last 6 months)
    monthly_trend = []
    for i in range(5, -1, -1):
        month_date = today.replace(day=1) - timedelta(days=30*i)
        month_expenses = Transaction.objects.filter(
            user=request.user,
            transaction_type='expense',
            date__year=month_date.year,
            date__month=month_date.month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_trend.append({
            'month': month_date.strftime('%b'),
            'amount': float(month_expenses)
        })
    
    # Recent transactions
    recent_transactions = Transaction.objects.filter(
        user=request.user
    ).select_related('category').order_by('-date', '-created_at')[:10]
    
    # Budget alerts calculation
    budget_alerts = []
    expense_categories = Category.objects.filter(
        user=request.user,
        category_type='expense',
        monthly_budget__gt=0
    )
    
    for category in expense_categories:
        # Calculate total spent in current month for this category
        total_spent = monthly_transactions.filter(
            category=category,
            transaction_type='expense'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        if category.monthly_budget > 0:
            percentage = (total_spent / category.monthly_budget) * 100
            
            if percentage >= 80:  # Show alerts for 80% and above
                budget_alerts.append({
                    'category': category.name,
                    'spent': float(total_spent),
                    'budget': float(category.monthly_budget),
                    'percentage': float(percentage),
                    'level': 'danger' if percentage >= 100 else 'warning'
                })
    
    # Get user's categories for dashboard (pass as JSON for JavaScript)
    categories = Category.objects.filter(user=request.user)
    categories_json = json.dumps([{
        'id': str(cat.id),
        'name': cat.name,
        'icon': cat.icon,
        'type': cat.category_type
    } for cat in categories])
    
    context = {
        'income': income,
        'expenses': expenses,
        'balance': balance,
        'savings_rate': round(savings_rate, 1),
        'category_data': json.dumps(category_data),
        'monthly_trend': json.dumps(monthly_trend),
        'recent_transactions': recent_transactions,
        'budget_alerts': budget_alerts,
        'categories': categories,
        'categories_json': categories_json,
        'user_profile': user_profile,
    }
    
    return render(request, 'tracker/dashboard.html', context)

@login_required
def transactions_view(request):
    """All transactions with filtering"""
    transactions = Transaction.objects.filter(
        user=request.user
    ).select_related('category').order_by('-date', '-created_at')
    
    # Apply filters
    transaction_type = request.GET.get('type')
    category_id = request.GET.get('category')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if transaction_type and transaction_type != 'all':
        transactions = transactions.filter(transaction_type=transaction_type)
    
    if category_id and category_id != 'all':
        transactions = transactions.filter(category_id=category_id)
    
    if date_from:
        transactions = transactions.filter(date__gte=date_from)
    
    if date_to:
        transactions = transactions.filter(date__lte=date_to)
    
    # Calculate total
    transactions_total = transactions.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    
    # Get user profile for currency
    user_profile = get_user_profile(request.user)
    
    # Get categories for filter dropdown
    categories = Category.objects.filter(user=request.user)
    
    context = {
        'transactions': transactions,
        'categories': categories,
        'transactions_total': transactions_total,
        'user_profile': user_profile,
    }
    
    return render(request, 'tracker/transactions.html', context)

@login_required
def categories_view(request):
    """Categories and budgets management"""
    expense_categories = Category.objects.filter(
        user=request.user,
        category_type='expense'
    )
    
    income_categories = Category.objects.filter(
        user=request.user,
        category_type='income'
    )
    
    # Calculate totals
    today = timezone.now().date()
    current_month = today.replace(day=1)
    
    total_budget = sum(cat.monthly_budget for cat in expense_categories)
    
    total_spent = Transaction.objects.filter(
        user=request.user,
        transaction_type='expense',
        date__year=current_month.year,
        date__month=current_month.month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    remaining = total_budget - total_spent
    
    # Get user profile for currency
    user_profile = get_user_profile(request.user)
    
    context = {
        'expense_categories': expense_categories,
        'income_categories': income_categories,
        'total_budget': total_budget,
        'total_spent': total_spent,
        'remaining': remaining,
        'user_profile': user_profile,
    }
    
    return render(request, 'tracker/categories.html', context)


@login_required
def reports_view(request):
    """Financial reports generation"""
    today = timezone.now().date()
    
    # Year-to-date summary
    ytd_income = Transaction.objects.filter(
        user=request.user,
        transaction_type='income',
        date__year=today.year
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    ytd_expenses = Transaction.objects.filter(
        user=request.user,
        transaction_type='expense',
        date__year=today.year
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    ytd_savings = ytd_income - ytd_expenses
    
    # Top spending categories
    top_categories = Transaction.objects.filter(
        user=request.user,
        transaction_type='expense',
        date__year=today.year
    ).values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')[:5]
    
    # Get user profile for currency
    user_profile = get_user_profile(request.user)
    
    context = {
        'ytd_income': ytd_income,
        'ytd_expenses': ytd_expenses,
        'ytd_savings': ytd_savings,
        'top_categories': top_categories,
        'user_profile': user_profile,
    }
    
    return render(request, 'tracker/reports.html', context)


@login_required
def profile_view(request):
    """User profile and settings"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save()
            
            # Update user info
            user = request.user
            user.first_name = form.cleaned_data.get('first_name', '')
            user.last_name = form.cleaned_data.get('last_name', '')
            user.email = form.cleaned_data.get('email', '')
            user.save()
            
            messages.success(request, 'Profile updated successfully')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
    }
    
    return render(request, 'tracker/profile.html', context)


# API Views
@login_required
@require_POST
def create_transaction(request):
    """Create a new transaction via AJAX"""
    try:
        # Parse form data
        transaction_type = request.POST.get('transaction-type')
        amount = request.POST.get('amount')
        category_id = request.POST.get('category')
        date = request.POST.get('date')
        description = request.POST.get('description')
        payment_method = request.POST.get('payment_method', 'cash')
        
        # Validate required fields
        if not all([transaction_type, amount, category_id, date]):
            return JsonResponse({
                'success': False,
                'errors': 'Missing required fields'
            }, status=400)
        
        # Get category
        try:
            category = Category.objects.get(id=category_id, user=request.user)
        except Category.DoesNotExist:
            return JsonResponse({
                'success': False,
                'errors': 'Invalid category'
            }, status=400)
        
        # Create transaction
        transaction = Transaction.objects.create(
            user=request.user,
            transaction_type=transaction_type,
            amount=amount,
            category=category,
            date=date,
            description=description or '',
            payment_method=payment_method
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Transaction added successfully',
            'transaction_id': str(transaction.id)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'errors': str(e)
        }, status=400)


@login_required
@require_POST
def create_category(request):
    """Create a new category via AJAX"""
    try:
        name = request.POST.get('name')
        category_type = request.POST.get('category-type')
        icon = request.POST.get('icon', '📦')
        monthly_budget = request.POST.get('monthly_budget', 0)
        
        if not all([name, category_type]):
            return JsonResponse({
                'success': False,
                'errors': 'Name and type are required'
            }, status=400)
        
        # Check for duplicate category
        if Category.objects.filter(
            user=request.user,
            name=name,
            category_type=category_type
        ).exists():
            return JsonResponse({
                'success': False,
                'errors': 'Category already exists'
            }, status=400)
        
        # Create category
        category = Category.objects.create(
            user=request.user,
            name=name,
            category_type=category_type,
            icon=icon,
            monthly_budget=monthly_budget if category_type == 'expense' else 0
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Category added successfully',
            'category_id': str(category.id)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'errors': str(e)
        }, status=400)


@login_required
@require_GET
def download_csv(request):
    """Download transactions as CSV"""
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Category', 'Description', 'Amount', 'Payment Method'])
    
    for transaction in transactions:
        writer.writerow([
            transaction.date,
            transaction.get_transaction_type_display(),
            transaction.category.name if transaction.category else '',
            transaction.description,
            transaction.amount,
            transaction.get_payment_method_display(),
        ])
    
    return response


# Helper Functions
def create_default_categories(user):
    """Create default categories for new user"""
    default_categories = [
        # Expense categories
        ('Food', 'expense', '🍔', 0),
        ('Transport', 'expense', '🚗', 0),
        ('Shopping', 'expense', '🛍️', 0),
        ('Bills', 'expense', '📄', 0),
        ('Entertainment', 'expense', '🎬', 0),
        ('Other', 'expense', '📦', 0),
        
        # Income categories
        ('Salary', 'income', '💼', 0),
        ('Freelance', 'income', '💻', 0),
        ('Gifts', 'income', '🎁', 0),
        ('Other Income', 'income', '💰', 0),
    ]
    
    categories = []
    for name, category_type, icon, budget in default_categories:
        categories.append(Category(
            user=user,
            name=name,
            category_type=category_type,
            icon=icon,
            monthly_budget=budget,
            is_default=True
        ))
    
    Category.objects.bulk_create(categories)

# REST API Views
@login_required
@require_POST
def update_transaction(request, transaction_id):
    """Update an existing transaction"""
    try:
        transaction = Transaction.objects.get(id=transaction_id, user=request.user)
        
        # Parse form data
        transaction_type = request.POST.get('transaction-type')
        amount = request.POST.get('amount')
        category_id = request.POST.get('category')
        date = request.POST.get('date')
        description = request.POST.get('description')
        payment_method = request.POST.get('payment_method')
        
        # Update fields
        if transaction_type:
            transaction.transaction_type = transaction_type
        if amount:
            transaction.amount = amount
        if category_id:
            try:
                category = Category.objects.get(id=category_id, user=request.user)
                transaction.category = category
            except Category.DoesNotExist:
                pass
        if date:
            transaction.date = date
        if description is not None:
            transaction.description = description
        if payment_method:
            transaction.payment_method = payment_method
        
        transaction.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Transaction updated successfully'
        })
        
    except Transaction.DoesNotExist:
        return JsonResponse({
            'success': False,
            'errors': 'Transaction not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'errors': str(e)
        }, status=400)


@login_required
@require_POST
def delete_transaction(request, transaction_id):
    """Delete a transaction"""
    try:
        transaction = Transaction.objects.get(id=transaction_id, user=request.user)
        transaction.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Transaction deleted successfully'
        })
        
    except Transaction.DoesNotExist:
        return JsonResponse({
            'success': False,
            'errors': 'Transaction not found'
        }, status=404)


@login_required
@require_POST
def update_category(request, category_id):
    """Update an existing category"""
    try:
        category = Category.objects.get(id=category_id, user=request.user)
        
        name = request.POST.get('name')
        category_type = request.POST.get('category-type')
        icon = request.POST.get('icon')
        monthly_budget = request.POST.get('monthly_budget')
        
        # Update fields
        if name:
            category.name = name
        if category_type:
            category.category_type = category_type
        if icon is not None:
            category.icon = icon
        if monthly_budget is not None:
            category.monthly_budget = monthly_budget if category_type == 'expense' else 0
        
        category.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Category updated successfully'
        })
        
    except Category.DoesNotExist:
        return JsonResponse({
            'success': False,
            'errors': 'Category not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'errors': str(e)
        }, status=400)


@login_required
@require_POST
def delete_category(request, category_id):
    """Delete a category"""
    try:
        category = Category.objects.get(id=category_id, user=request.user)
        
        # Don't delete default categories
        if category.is_default:
            return JsonResponse({
                'success': False,
                'errors': 'Cannot delete default categories'
            }, status=400)
        
        category.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Category deleted successfully'
        })
        
    except Category.DoesNotExist:
        return JsonResponse({
            'success': False,
            'errors': 'Category not found'
        }, status=404)

# REST API endpoints
@login_required
@require_GET
def api_dashboard_summary(request):
    """API endpoint for dashboard data"""
    today = timezone.now().date()
    current_month = today.replace(day=1)
    
    monthly_transactions = Transaction.objects.filter(
        user=request.user,
        date__year=current_month.year,
        date__month=current_month.month
    )
    
    income = monthly_transactions.filter(transaction_type='income').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    
    expenses = monthly_transactions.filter(transaction_type='expense').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    
    balance = income - expenses
    savings_rate = (balance / income * 100) if income > 0 else 0
    
    return JsonResponse({
        'income': float(income),
        'expenses': float(expenses),
        'balance': float(balance),
        'savings_rate': round(float(savings_rate), 1),
    })


@login_required
@require_GET
def api_recent_transactions(request):
    """API endpoint for recent transactions"""
    transactions = Transaction.objects.filter(
        user=request.user
    ).select_related('category').order_by('-date', '-created_at')[:10]
    
    data = [
        {
            'id': str(t.id),
            'date': t.date.strftime('%Y-%m-%d'),
            'type': t.transaction_type,
            'category': t.category.name if t.category else '',
            'description': t.description,
            'amount': float(t.amount),
            'payment_method': t.get_payment_method_display(),
        }
        for t in transactions
    ]
    
    return JsonResponse(data, safe=False)