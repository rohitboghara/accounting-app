from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal
from apps.masters.models import Account, CompanyProfile
from apps.core.models import User

class JournalVoucher(models.Model):
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='vouchers', null=True)
    STATUS_DRAFT = 'draft'
    STATUS_REVIEWED = 'reviewed'
    STATUS_POSTED = 'posted'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_REVIEWED, 'Reviewed (Pending Posting)'),
        (STATUS_POSTED, 'Posted'),
    ]
    voucher_number = models.CharField(max_length=30)
    date = models.DateField()
    narration = models.TextField(blank=True)
    reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='vouchers_created')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='vouchers_reviewed')
    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='vouchers_posted')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        unique_together = ['company', 'voucher_number']
        verbose_name = 'Journal Voucher'

    def __str__(self):
        return f"JV-{self.voucher_number} ({self.date})"

    def get_total_debit(self):
        return self.lines.aggregate(t=models.Sum('debit_amount'))['t'] or Decimal('0')

    def get_total_credit(self):
        return self.lines.aggregate(t=models.Sum('credit_amount'))['t'] or Decimal('0')

    def is_balanced(self):
        return self.get_total_debit() == self.get_total_credit()

    def clean(self):
        if self.pk and not self.is_balanced():
            raise ValidationError('Total debit must equal total credit.')

    @classmethod
    def generate_voucher_number(cls, company):
        from datetime import date
        today = date.today()
        prefix = f"JV{today.strftime('%Y%m%d')}"
        last = cls.objects.filter(company=company, voucher_number__startswith=prefix).order_by('-voucher_number').first()
        seq = (int(last.voucher_number[-4:]) + 1) if last else 1
        return f"{prefix}{seq:04d}"

class JournalVoucherLine(models.Model):
    voucher = models.ForeignKey(JournalVoucher, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    description = models.CharField(max_length=300, blank=True)
    debit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    credit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    has_gst = models.BooleanField(default=False)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    taxable_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    cgst_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    sgst_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    igst_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    gst_type = models.CharField(max_length=10, choices=[('intra', 'Intra-State (CGST+SGST)'), ('inter', 'Inter-State (IGST)')], blank=True)
    line_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['line_order', 'pk']

class VoucherAttachment(models.Model):
    voucher = models.ForeignKey(JournalVoucher, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='vouchers/%Y/%m/')
    name = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

class AuditLog(models.Model):
    voucher = models.ForeignKey(JournalVoucher, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True)

class RecurringVoucher(models.Model):
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='recurring_templates', null=True)
    name = models.CharField(max_length=100)
    day_of_month = models.PositiveSmallIntegerField(default=1)
    last_generated = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    narration = models.TextField(blank=True)

class RecurringVoucherLine(models.Model):
    template = models.ForeignKey(RecurringVoucher, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    debit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description = models.CharField(max_length=300, blank=True)
