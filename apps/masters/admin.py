from django.contrib import admin
from .models import CompanyProfile, Account


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'gstin', 'pan', 'financial_year']


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'account_type', 'is_active']
    list_filter = ['category', 'account_type', 'is_active']
    search_fields = ['code', 'name']
