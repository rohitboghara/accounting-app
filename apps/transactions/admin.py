from django.contrib import admin
from .models import JournalVoucher, JournalVoucherLine


class JournalVoucherLineInline(admin.TabularInline):
    model = JournalVoucherLine
    extra = 0


@admin.register(JournalVoucher)
class JournalVoucherAdmin(admin.ModelAdmin):
    list_display = ['voucher_number', 'date', 'status', 'created_by']
    list_filter = ['status', 'date']
    inlines = [JournalVoucherLineInline]
