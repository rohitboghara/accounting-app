from django.urls import path
from . import views

urlpatterns = [
    path('', views.report_index, name='report_index'),
    path('ledger/', views.ledger_report, name='ledger_report'),
    path('trial-balance/', views.trial_balance, name='trial_balance'),
    path('profit-loss/', views.profit_loss, name='profit_loss'),
    path('balance-sheet/', views.balance_sheet, name='balance_sheet'),
    path('gst/', views.gst_report, name='gst_report'),
    path('aging/', views.aging_report, name='aging_report'),
    path('budget/', views.budget_report, name='budget_report'),
]
