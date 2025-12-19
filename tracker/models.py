from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator
import uuid


class Category(models.Model):
    """
    Expense/Income Categories
    """
    CATEGORY_TYPES = (
        ('income', 'Income'),
        ('expense', 'Expense'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=10, choices=CATEGORY_TYPES)
    icon = models.CharField(max_length=10, default='📦')
    monthly_budget = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00,
        validators=[MinValueValidator(0)],
        help_text="Monthly budget limit (for expense categories only)"
    )
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        unique_together = ['user', 'name', 'category_type']
        ordering = ['category_type', 'name']
    
    def __str__(self):
        return f"{self.get_category_type_display()}: {self.name}"


class Transaction(models.Model):
    """
    Financial Transactions (Income/Expenses)
    """
    TRANSACTION_TYPES = (
        ('income', 'Income'),
        ('expense', 'Expense'),
    )
    
    # PAYMENT_METHODS defines the choices for the payment_method field
    # This creates a dropdown in forms and ensures data integrity
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('bank', 'Bank Transfer'),
        ('mobile', 'Mobile Payment'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='transactions'
    )
    description = models.TextField(blank=True)
    date = models.DateField(default=timezone.now)
    payment_method = models.CharField(
        max_length=20, 
        choices=PAYMENT_METHODS, 
        default='cash'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'transaction_type']),
        ]
    
    def __str__(self):
        return f"{self.transaction_type}: {self.amount} - {self.description[:50]}"
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('transaction_detail', args=[str(self.id)])


class UserProfile(models.Model):
    """
    Extended User Profile
    """
    CURRENCY_CHOICES = (
        ('birr', 'Ethiopian Birr (ETB)'),
        ('usd', 'US Dollar ($)'),
        ('eur', 'Euro (€)'),
        ('gbp', 'British Pound (£)'),
    )
    
    TIMEZONE_CHOICES = (
        ('Africa/Addis_Ababa', 'Africa/Addis Ababa (EAT)'),
        ('UTC', 'UTC'),
        ('America/New_York', 'America/New York (EST)'),
        ('Europe/London', 'Europe/London (GMT)'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='birr')
    timezone = models.CharField(max_length=50, choices=TIMEZONE_CHOICES, default='Africa/Addis_Ababa')
    enable_notifications = models.BooleanField(default=True)
    dark_mode = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile for {self.user.username}"
    
    @property
    def currency_symbol(self):
        symbols = {
            'birr': 'birr',
            'usd': '$',
            'eur': '€',
            'gbp': '£',
        }
        return symbols.get(self.currency, 'birr')


class BudgetAlert(models.Model):
    """
    Budget Alert Settings
    """
    ALERT_TYPES = (
        ('warning', 'Warning (80%)'),
        ('danger', 'Danger (100%)'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budget_alerts')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=10, choices=ALERT_TYPES, default='warning')
    threshold_percentage = models.IntegerField(default=80)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'category']
    
    def __str__(self):
        return f"Alert for {self.category.name} at {self.threshold_percentage}%"


class FinancialReport(models.Model):
    """
    Generated Financial Reports
    """
    REPORT_TYPES = (
        ('summary', 'Monthly Summary'),
        ('detailed', 'Detailed Transactions'),
        ('category', 'Category Breakdown'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    month = models.DateField()
    data = models.JSONField(default=dict)  # Store report data as JSON
    file_path = models.FileField(upload_to='reports/', null=True, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"{self.report_type} Report - {self.month.strftime('%B %Y')}"