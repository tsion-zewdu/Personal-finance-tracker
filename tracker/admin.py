from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import (
    Category, Transaction, UserProfile, 
    BudgetAlert, FinancialReport
)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'category', 'date', 'payment_method')
    list_filter = ('transaction_type', 'date', 'payment_method')
    search_fields = ('description', 'user__username')
    readonly_fields = ('created_at', 'updated_at')


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'category_type', 'monthly_budget', 'is_default')
    list_filter = ('category_type', 'is_default')
    search_fields = ('name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')


class BudgetAlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'threshold_percentage', 'is_active')
    list_filter = ('is_active', 'alert_type')


class FinancialReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'report_type', 'month', 'generated_at')
    list_filter = ('report_type', 'month')
    readonly_fields = ('generated_at',)


# Register models
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(UserProfile)
admin.site.register(BudgetAlert, BudgetAlertAdmin)
admin.site.register(FinancialReport, FinancialReportAdmin)