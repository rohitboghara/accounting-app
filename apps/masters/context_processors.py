from .models import CompanyProfile

def company_profile(request):
    if not request.user.is_authenticated:
        return {}
        
    companies = CompanyProfile.objects.all()
    active_company_id = request.session.get('active_company_id')
    
    active_company = None
    if active_company_id:
        active_company = CompanyProfile.objects.filter(id=active_company_id).first()
        
    if not active_company and companies.exists():
        active_company = companies.first()
        request.session['active_company_id'] = active_company.id
        
    return {
        'company': active_company,
        'all_companies': companies
    }
