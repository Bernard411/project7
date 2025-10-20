from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard', views.dashboard, name='dashboard'),
    
    # Authentication
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Loans
    path('apply-loan/', views.apply_for_loan, name='apply_loan'),
    path('loan/<int:loan_id>/', views.loan_detail, name='loan_detail'),
    path('loan/<int:loan_id>/pay/', views.make_payment, name='make_payment'),
    path('loan-history/', views.loan_history, name='loan_history'),
    
    # Social
    path('vouch/', views.vouch_for_user, name='vouch_for_user'),
    
    # Savings
    path('add-savings/', views.add_savings, name='add_savings'),
    path('savings-history/', views.savings_history, name='savings_history'),
    
    # Verification
    path('verify-mobile-money/', views.verify_mobile_money, name='verify_mobile_money'),
    
    # Score
    path('score-breakdown/', views.score_breakdown, name='score_breakdown'),
]