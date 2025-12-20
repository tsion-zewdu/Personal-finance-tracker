from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('', views.welcome_view, name='welcome'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('logout/', views.logout_view, name='logout'),
    
    # Main Application URLs
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('transactions/', views.transactions_view, name='transactions'),
    path('categories/', views.categories_view, name='categories'),
    path('reports/', views.reports_view, name='reports'),
    path('profile/', views.profile_view, name='profile'),
    
    # API/Functional URLs
    path('api/transactions/create/', views.create_transaction, name='create_transaction'),
    path('api/transactions/<uuid:transaction_id>/update/', views.update_transaction, name='update_transaction'),
    path('api/transactions/<uuid:transaction_id>/delete/', views.delete_transaction, name='delete_transaction'),
    path('api/categories/create/', views.create_category, name='create_category'),
    path('api/categories/<uuid:category_id>/update/', views.update_category, name='update_category'),
    path('api/categories/<uuid:category_id>/delete/', views.delete_category, name='delete_category'),
    path('download-csv/', views.download_csv, name='download_csv'),
]