from django.db import models

class CompanyProfile(models.Model):
    FINANCIAL_YEAR_CHOICES = [
        ('2023-2024', '2023-2024'),
        ('2024-2025', '2024-2025'),
        ('2025-2026', '2025-2026'),
        ('2026-2027', '2026-2027'),
    ]
    name = models.CharField(max_length=200)
    gstin = models.CharField(max_length=15, blank=True, verbose_name='GSTIN')
    pan = models.CharField(max_length=10, blank=True, verbose_name='PAN')
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    financial_year = models.CharField(max_length=20, choices=FINANCIAL_YEAR_CHOICES, default='2024-2025')
    logo = models.ImageField(upload_to='company/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Company Profile'

    def __str__(self):
        return self.name

    def fy_start(self):
        year = int(self.financial_year.split('-')[0])
        from datetime import date
        return date(year, 4, 1)

    def fy_end(self):
        year = int(self.financial_year.split('-')[1])
        from datetime import date
        return date(year, 3, 31)

class Account(models.Model):
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='accounts', null=True)
    CATEGORY_CHOICES = [
        ('assets', 'Assets'),
        ('liabilities', 'Liabilities'),
        ('income', 'Income'),
        ('expenses', 'Expenses'),
        ('equity', 'Equity'),
    ]
    TYPE_CHOICES = [
        ('bank', 'Bank'), ('cash', 'Cash'), ('receivable', 'Accounts Receivable'),
        ('payable', 'Accounts Payable'), ('fixed_asset', 'Fixed Asset'),
        ('current_asset', 'Current Asset'), ('current_liability', 'Current Liability'),
        ('long_term_liability', 'Long Term Liability'), ('revenue', 'Revenue'),
        ('cost_of_goods', 'Cost of Goods Sold'), ('operating_expense', 'Operating Expense'),
        ('other_income', 'Other Income'), ('other_expense', 'Other Expense'),
        ('equity', 'Equity'), ('tax', 'Tax'), ('other', 'Other'),
    ]
    code = models.CharField(max_length=20) # Removed unique=True globally, will be unique per company
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    account_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='other')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')
    description = models.TextField(blank=True)
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    opening_balance_type = models.CharField(max_length=6, choices=[('debit', 'Debit'), ('credit', 'Credit')], default='debit')
    is_active = models.BooleanField(default=True)
    is_gst_account = models.BooleanField(default=False)
    gstin = models.CharField(max_length=15, blank=True, verbose_name='GSTIN')
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    contact_person = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']
        unique_together = ['company', 'code']
        verbose_name = 'Account'

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_balance(self, as_of_date=None, from_date=None):
        from apps.transactions.models import JournalVoucherLine
        from decimal import Decimal
        qs = JournalVoucherLine.objects.filter(account=self)
        if as_of_date: qs = qs.filter(voucher__date__lte=as_of_date)
        if from_date: qs = qs.filter(voucher__date__gte=from_date)
        agg = qs.aggregate(td=models.Sum('debit_amount'), tc=models.Sum('credit_amount'))
        td, tc = agg['td'] or Decimal('0'), agg['tc'] or Decimal('0')
        return td, tc, (td - tc if self.category in ('assets', 'expenses') else tc - td)

class Budget(models.Model):
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='budgets', null=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='budgets')
    month = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['company', 'account', 'month']
        verbose_name = 'Budget'
