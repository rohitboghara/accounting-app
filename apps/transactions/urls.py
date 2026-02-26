from django.urls import path
from . import views

urlpatterns = [
    path('', views.voucher_list, name='voucher_list'),
    path('create/', views.voucher_create, name='voucher_create'),
    path('<int:pk>/', views.voucher_detail, name='voucher_detail'),
    path('<int:pk>/edit/', views.voucher_edit, name='voucher_edit'),
    path('<int:pk>/delete/', views.voucher_delete, name='voucher_delete'),
    path('<int:pk>/restore/', views.voucher_restore, name='voucher_restore'),
    path('<int:pk>/post/', views.voucher_post, name='voucher_post'),
    path('<int:pk>/review/', views.voucher_review, name='voucher_review'),
    path('api/accounts/', views.get_accounts_json, name='accounts_json'),
    path('import-csv/', views.voucher_import_csv, name='voucher_import_csv'),
    path('recurring/generate/', views.generate_recurring_vouchers, name='generate_recurring_vouchers'),
]
