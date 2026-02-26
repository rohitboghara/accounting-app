from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
from .models import JournalVoucher, JournalVoucherLine, AuditLog, RecurringVoucher, RecurringVoucherLine
from apps.masters.models import Account, CompanyProfile
import json
import csv
import io
from datetime import date


@login_required
def voucher_list(request):
    active_id = request.session.get('active_company_id')
    show_trash = request.GET.get('trash') == '1'
    vouchers = JournalVoucher.objects.filter(company_id=active_id, is_deleted=show_trash).select_related('created_by')
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        vouchers = vouchers.filter(status=status_filter)
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        vouchers = vouchers.filter(date__gte=date_from)
    if date_to:
        vouchers = vouchers.filter(date__lte=date_to)
    return render(request, 'transactions/voucher_list.html', {
        'vouchers': vouchers,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
def voucher_create(request):
    active_id = request.session.get('active_company_id')
    accounts = Account.objects.filter(company_id=active_id, is_active=True).order_by('code')
    if request.method == 'POST':
        return _save_voucher(request, None)
    context = {
        'accounts': accounts,
        'today': date.today().isoformat(),
        'voucher_number': JournalVoucher.generate_voucher_number(CompanyProfile.objects.get(id=active_id)),
        'title': 'New Journal Voucher',
    }
    return render(request, 'transactions/voucher_form.html', context)


@login_required
def voucher_edit(request, pk):
    active_id = request.session.get('active_company_id')
    voucher = get_object_or_404(JournalVoucher, pk=pk, company_id=active_id)
    if voucher.status == 'posted' and not request.user.is_admin():
        messages.error(request, 'Posted vouchers can only be edited by admins.')
        return redirect('voucher_detail', pk=pk)
    accounts = Account.objects.filter(company_id=active_id, is_active=True).order_by('code')
    if request.method == 'POST':
        return _save_voucher(request, voucher)
    lines_data = []
    for line in voucher.lines.all():
        lines_data.append({
            'account_id': line.account_id,
            'description': line.description,
            'debit_amount': str(line.debit_amount),
            'credit_amount': str(line.credit_amount),
            'has_gst': line.has_gst,
            'gst_rate': str(line.gst_rate or ''),
            'taxable_value': str(line.taxable_value or ''),
            'cgst_amount': str(line.cgst_amount or ''),
            'sgst_amount': str(line.sgst_amount or ''),
            'igst_amount': str(line.igst_amount or ''),
            'gst_type': line.gst_type or 'intra',
        })
    context = {
        'voucher': voucher,
        'accounts': accounts,
        'lines_json': json.dumps(lines_data),
        'title': f'Edit Voucher - {voucher.voucher_number}',
        'voucher_number': voucher.voucher_number,
        'today': voucher.date.isoformat() if voucher.date else date.today().isoformat(),
    }
    return render(request, 'transactions/voucher_form.html', context)


def _save_voucher(request, voucher):
    try:
        with transaction.atomic():
            voucher_number = request.POST.get('voucher_number', '').strip()
            vdate = request.POST.get('date', '')
            narration = request.POST.get('narration', '')
            reference = request.POST.get('reference', '')
            status = request.POST.get('status', 'draft')

            if not vdate:
                messages.error(request, 'Date is required.')
                return redirect('voucher_create')

            # Parse lines from POST
            account_ids = request.POST.getlist('account_id[]')
            descriptions = request.POST.getlist('description[]')
            debit_amounts = request.POST.getlist('debit_amount[]')
            credit_amounts = request.POST.getlist('credit_amount[]')
            has_gsts = request.POST.getlist('has_gst[]')
            gst_rates = request.POST.getlist('gst_rate[]')
            taxable_values = request.POST.getlist('taxable_value[]')
            cgst_amounts = request.POST.getlist('cgst_amount[]')
            sgst_amounts = request.POST.getlist('sgst_amount[]')
            igst_amounts = request.POST.getlist('igst_amount[]')
            gst_types = request.POST.getlist('gst_type[]')

            if not account_ids:
                messages.error(request, 'At least one line is required.')
                return redirect('voucher_create')

            # Build line objects to validate
            lines = []
            total_debit = Decimal('0')
            total_credit = Decimal('0')

            for i, acc_id in enumerate(account_ids):
                if not acc_id:
                    continue
                try:
                    account = Account.objects.get(pk=acc_id)
                except Account.DoesNotExist:
                    messages.error(request, f'Invalid account on line {i+1}.')
                    return redirect('voucher_create')

                def safe_decimal(val, default='0'):
                    try:
                        v = Decimal(val) if val else Decimal(default)
                        return max(v, Decimal('0'))
                    except InvalidOperation:
                        return Decimal(default)

                debit = safe_decimal(debit_amounts[i] if i < len(debit_amounts) else '0')
                credit = safe_decimal(credit_amounts[i] if i < len(credit_amounts) else '0')
                has_gst = (has_gsts[i] if i < len(has_gsts) else '') == 'true'

                total_debit += debit
                total_credit += credit

                line_data = {
                    'account': account,
                    'description': descriptions[i] if i < len(descriptions) else '',
                    'debit_amount': debit,
                    'credit_amount': credit,
                    'has_gst': has_gst,
                    'gst_rate': safe_decimal(gst_rates[i] if i < len(gst_rates) else '', '0') if has_gst else None,
                    'taxable_value': safe_decimal(taxable_values[i] if i < len(taxable_values) else '', '0') if has_gst else None,
                    'cgst_amount': safe_decimal(cgst_amounts[i] if i < len(cgst_amounts) else '', '0') if has_gst else None,
                    'sgst_amount': safe_decimal(sgst_amounts[i] if i < len(sgst_amounts) else '', '0') if has_gst else None,
                    'igst_amount': safe_decimal(igst_amounts[i] if i < len(igst_amounts) else '', '0') if has_gst else None,
                    'gst_type': gst_types[i] if i < len(gst_types) else 'intra',
                    'line_order': i,
                }
                lines.append(line_data)

            if len(lines) < 2:
                messages.error(request, 'A journal entry needs at least 2 lines.')
                return redirect('voucher_create')

            if total_debit != total_credit:
                messages.error(request, f'Voucher not balanced! Total Debit: ₹{total_debit} ≠ Total Credit: ₹{total_credit}')
                return redirect('voucher_create' if not voucher else 'voucher_edit', pk=voucher.pk if voucher else None)

            if total_debit == 0:
                messages.error(request, 'Voucher amounts cannot be zero.')
                return redirect('voucher_create')

            # Save voucher
            active_id = request.session.get('active_company_id')
            is_new = not voucher
            if not voucher:
                voucher = JournalVoucher(created_by=request.user, company_id=active_id)
            voucher.voucher_number = voucher_number or JournalVoucher.generate_voucher_number(CompanyProfile.objects.get(id=active_id))
            voucher.date = vdate
            voucher.narration = narration
            voucher.reference = reference
            voucher.status = status
            voucher.save()

            # Handle Attachments
            from .models import VoucherAttachment
            files = request.FILES.getlist('attachments')
            for f in files:
                VoucherAttachment.objects.create(voucher=voucher, file=f, name=f.name)

            # Audit Log
            AuditLog.objects.create(
                voucher=voucher,
                user=request.user,
                action='create' if is_new else 'update'
            )

            # Delete old lines and recreate
            voucher.lines.all().delete()
            for ld in lines:
                JournalVoucherLine.objects.create(voucher=voucher, **ld)

            messages.success(request, f'Voucher {voucher.voucher_number} saved successfully.')
            return redirect('voucher_detail', pk=voucher.pk)

    except Exception as e:
        messages.error(request, f'Error saving voucher: {str(e)}')
        if voucher and voucher.pk:
            return redirect('voucher_edit', pk=voucher.pk)
        return redirect('voucher_create')


@login_required
def voucher_detail(request, pk):
    voucher = get_object_or_404(JournalVoucher, pk=pk)
    lines = voucher.lines.select_related('account').all()
    return render(request, 'transactions/voucher_detail.html', {
        'voucher': voucher,
        'lines': lines,
    })


@login_required
def voucher_delete(request, pk):
    if not request.user.is_admin():
        messages.error(request, 'Only admins can delete vouchers.')
        return redirect('voucher_list')
    voucher = get_object_or_404(JournalVoucher, pk=pk)
    if request.method == 'POST':
        voucher.is_deleted = True
        import django.utils.timezone as tz
        voucher.deleted_at = tz.now()
        voucher.save()
        
        AuditLog.objects.create(voucher=voucher, user=request.user, action='delete')
        
        messages.success(request, 'Voucher moved to trash.')
        return redirect('voucher_list')
    return render(request, 'transactions/voucher_confirm_delete.html', {'voucher': voucher})


@login_required
def voucher_restore(request, pk):
    if not request.user.is_admin():
        messages.error(request, 'Only admins can restore vouchers.')
        return redirect('voucher_list')
    voucher = get_object_or_404(JournalVoucher, pk=pk)
    voucher.is_deleted = False
    voucher.deleted_at = None
    voucher.save()
    
    AuditLog.objects.create(voucher=voucher, user=request.user, action='restore')
    
    messages.success(request, 'Voucher restored successfully.')
    return redirect('voucher_detail', pk=voucher.pk)


@login_required
def voucher_post(request, pk):
    if not request.user.is_admin():
        messages.error(request, 'Only admins can post vouchers.')
        return redirect('voucher_detail', pk=pk)
    voucher = get_object_or_404(JournalVoucher, pk=pk)
    if voucher.is_balanced():
        voucher.status = 'posted'
        voucher.posted_by = request.user
        voucher.save()
        AuditLog.objects.create(voucher=voucher, user=request.user, action='post')
        messages.success(request, 'Voucher posted successfully.')
    else:
        messages.error(request, 'Cannot post unbalanced voucher.')
    return redirect('voucher_detail', pk=pk)


@login_required
def voucher_review(request, pk):
    if not request.user.is_admin():
        messages.error(request, 'Only admins can review vouchers.')
        return redirect('voucher_detail', pk=pk)
    voucher = get_object_or_404(JournalVoucher, pk=pk)
    if voucher.is_balanced():
        voucher.status = 'reviewed'
        voucher.reviewed_by = request.user
        voucher.save()
        AuditLog.objects.create(voucher=voucher, user=request.user, action='review')
        messages.success(request, 'Voucher reviewed successfully.')
    else:
        messages.error(request, 'Cannot review unbalanced voucher.')
    return redirect('voucher_detail', pk=pk)


@login_required
def voucher_import_csv(request):
    """Bulk upload journal entries from CSV"""
    active_id = request.session.get('active_company_id')
    company = CompanyProfile.objects.get(id=active_id)
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        vouchers_data = {}
        try:
            with transaction.atomic():
                for row in reader:
                    vnum = row['voucher_number']
                    if vnum not in vouchers_data:
                        vouchers_data[vnum] = {
                            'date': row['date'],
                            'narration': row.get('narration', ''),
                            'lines': []
                        }
                    acc = Account.objects.get(company_id=active_id, code=row['account_code'])
                    vouchers_data[vnum]['lines'].append({
                        'account': acc,
                        'description': row.get('description', ''),
                        'debit': Decimal(row.get('debit', '0')),
                        'credit': Decimal(row.get('credit', '0')),
                    })
                
                for vnum, data in vouchers_data.items():
                    voucher = JournalVoucher.objects.create(
                        company=company,
                        voucher_number=vnum, date=data['date'],
                        narration=data['narration'], created_by=request.user
                    )
                    for l in data['lines']:
                        JournalVoucherLine.objects.create(
                            voucher=voucher, account=l['account'],
                            description=l['description'],
                            debit_amount=l['debit'], credit_amount=l['credit']
                        )
                    AuditLog.objects.create(voucher=voucher, user=request.user, action='create')
            messages.success(request, f"Imported {len(vouchers_data)} vouchers.")
        except Exception as e:
            messages.error(request, f"Import failed: {str(e)}")
        return redirect('voucher_list')
    return render(request, 'transactions/import_csv.html')


@login_required
def generate_recurring_vouchers(request):
    """Generate vouchers from active recurring templates for the current month"""
    active_id = request.session.get('active_company_id')
    company = CompanyProfile.objects.get(id=active_id)
    today = date.today()
    recurring = RecurringVoucher.objects.filter(company_id=active_id, is_active=True)
    count = 0
    
    with transaction.atomic():
        for rv in recurring:
            # Check if already generated for this month
            if rv.last_generated and rv.last_generated.month == today.month and rv.last_generated.year == today.year:
                continue
                
            v_date = today.replace(day=min(rv.day_of_month, 28))
            voucher = JournalVoucher.objects.create(
                company=company,
                voucher_number=JournalVoucher.generate_voucher_number(company),
                date=v_date,
                narration=f"Recurring: {rv.name} - {rv.narration}",
                created_by=request.user
            )
            for rl in rv.lines.all():
                JournalVoucherLine.objects.create(
                    voucher=voucher, account=rl.account,
                    description=rl.description,
                    debit_amount=rl.debit_amount, credit_amount=rl.credit_amount
                )
            rv.last_generated = today
            rv.save()
            AuditLog.objects.create(voucher=voucher, user=request.user, action='create')
            count += 1
            
    messages.success(request, f"Generated {count} recurring vouchers.")
    return redirect('voucher_list')


@login_required
def get_accounts_json(request):
    accounts = Account.objects.filter(is_active=True).values('id', 'code', 'name', 'category')
    return JsonResponse({'accounts': list(accounts)})
