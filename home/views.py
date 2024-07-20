from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, authenticate, login
from django.http import JsonResponse
from .forms import UploadFileForm, LoginForm, GenerateDTRForm, ShiftForm, MemberForm, PreferenceForm, PositionForm, BranchForm, AccountUpdateForm
from .models import AttendanceRecord, Shift, Period, Attendance, Member, Preference, Position, Branch
from django.contrib import messages
from datetime import date, timedelta, datetime as dt
from collections import defaultdict
import calendar
from django.utils import timezone
import logging
from django.contrib import messages
from django.db.models import Q


def index(request):
    return redirect('accounts/login/')

#auth//////////////////////////////
def login_view(request):
    form = LoginForm(request.POST or None)
    msg = None
    if request.method == 'POST':
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None and user.is_superuser:
                login(request, user)
                return redirect('/admin')
            elif user is not None and not user.is_superuser and user.is_staff:
                login(request, user)
                return redirect('/attendance-record/')
            else:
                msg= 'invalid credentials'
        else:
            msg = 'error validating form'
    return render(request, 'accounts/login.html', {'form': form, 'msg': msg})

def logout_view(request):
  logout(request)
  return redirect('login')



#generate dtr//////////////////////////

# Configure logging
logging.basicConfig(level=logging.DEBUG)

@login_required
def generate_attendance(request):
    data = dict()
    if request.method == 'POST':
        form = GenerateDTRForm(request.POST)
        if form.is_valid():
            year = int(form.cleaned_data['year'])
            month = int(form.cleaned_data['month'])

            start_date = date(year, month, 1)
            end_date = date(year, month, calendar.monthrange(year, month)[1])

            start_date = timezone.make_aware(dt.combine(start_date, dt.min.time()))
            end_date = timezone.make_aware(dt.combine(end_date, dt.min.time()))

            period, created = Period.objects.get_or_create(
                start_date=start_date,
                end_date=end_date,
                defaults={'description': start_date.strftime('%B')}
            )

            for member in Member.objects.all():
                current_date = start_date
                while current_date <= end_date:
                    attendance, created = Attendance.objects.get_or_create(
                        member=member,
                        period=period,
                        date=current_date,
                        defaults={
                            'days': current_date.strftime('%A'),
                            'total_time': "0:00",
                            'total_under_time': "0:00"
                        }
                    )

                    if not created:
                        attendance.am_in = None
                        attendance.am_out = None
                        attendance.pm_in = None
                        attendance.pm_out = None

                    shift = member.shift
                    attendance_records = AttendanceRecord.objects.filter(
                        user_id=member.biometric_id,
                        date=current_date
                    ).order_by('time')

                    am_in = None
                    am_out = None
                    pm_in = None
                    pm_out = None

                    for record in attendance_records:
                        record_time = timezone.make_aware(dt.combine(current_date.date(), record.time))
                        shift_am_in = timezone.make_aware(dt.combine(current_date.date(), shift.am_in)) if shift.am_in else None
                        shift_am_out = timezone.make_aware(dt.combine(current_date.date(), shift.am_out)) if shift.am_out else None
                        shift_pm_in_start_time = timezone.make_aware(dt.combine(current_date.date(), shift.pm_in_start_time)) if shift.pm_in_start_time else None
                        shift_pm_in = timezone.make_aware(dt.combine(current_date.date(), shift.pm_in)) if shift.pm_in else None
                        shift_pm_out = timezone.make_aware(dt.combine(current_date.date(), shift.pm_out)) if shift.pm_out else None

                        time_12hr_format = record.time.strftime('%I:%M %p')

                        if record.status == 'check-in':
                            if shift.period_type == 'Dual':
                                if record_time <= shift_pm_in_start_time:
                                    am_in = record.time
                                    attendance.am_in = time_12hr_format
                                elif record_time > shift_pm_in_start_time and record_time <= shift_pm_out:
                                    pm_in = record.time
                                    attendance.pm_in = time_12hr_format
                            else:
                                if record_time < shift_am_in and record_time < shift_pm_out:
                                    am_in = record.time
                                    attendance.am_in = time_12hr_format
                                elif record_time < shift_pm_out:
                                    am_in = record.time  
                                    attendance.am_in = time_12hr_format
                        elif record.status == 'check-out':
                            if shift.period_type == 'Dual':
                                if record_time > shift_am_in and record_time < shift_pm_out:
                                    am_out = record.time
                                    attendance.am_out = time_12hr_format
                                elif record_time > shift_pm_in:
                                    pm_out = record.time
                                    attendance.pm_out = time_12hr_format
                            else:
                                if record_time > shift_am_in and record_time > shift_pm_out:
                                    pm_out = record.time
                                    attendance.pm_out = time_12hr_format
                                elif record_time > shift_am_in:
                                    pm_out = record.time
                                    attendance.pm_out = time_12hr_format

                    total_time_seconds = 0
                    if shift.period_type == 'Dual':
                        if am_in and am_out:
                            if am_in > shift.am_in and am_out < shift.am_out:
                                total_time_seconds += (dt.combine(current_date, am_out) - dt.combine(current_date, am_in)).seconds
                            elif am_in > shift.am_in:
                                total_time_seconds += (dt.combine(current_date, shift.am_out) - dt.combine(current_date, am_in)).seconds
                            elif am_out < shift.am_out:
                                total_time_seconds += (dt.combine(current_date, am_out) - dt.combine(current_date, shift.am_in)).seconds
                            else:
                                total_time_seconds += (dt.combine(current_date, shift.am_out) - dt.combine(current_date, shift.am_in)).seconds

                        if pm_in and pm_out:
                            if pm_in > shift.pm_in and pm_out < shift.pm_out:
                                total_time_seconds += (dt.combine(current_date, pm_out) - dt.combine(current_date, pm_in)).seconds
                            elif pm_in > shift.pm_in:
                                total_time_seconds += (dt.combine(current_date, shift.pm_out) - dt.combine(current_date, pm_in)).seconds
                            elif pm_out < shift.pm_out:
                                total_time_seconds += (dt.combine(current_date, pm_out) - dt.combine(current_date, shift.pm_in)).seconds
                            else:
                                total_time_seconds += (dt.combine(current_date, shift.pm_out) - dt.combine(current_date, shift.pm_in)).seconds
                    else:
                        if am_in and pm_out:
                            if am_in > shift.am_in and pm_out < shift.pm_out:
                                total_time_seconds += (dt.combine(current_date, pm_out) - dt.combine(current_date, am_in)).seconds
                            elif am_in > shift.am_in:
                                total_time_seconds += (dt.combine(current_date, shift.pm_out) - dt.combine(current_date, am_in)).seconds
                            elif pm_out < shift.pm_out:
                                total_time_seconds += (dt.combine(current_date, pm_out) - dt.combine(current_date, shift.am_in)).seconds
                            else:
                                total_time_seconds += (dt.combine(current_date, shift.pm_out) - dt.combine(current_date, shift.am_in)).seconds

                    total_time_hours = total_time_seconds // 3600
                    total_time_minutes = (total_time_seconds % 3600) // 60
                    total_time_str = f"{total_time_hours}:{total_time_minutes:02d}"
                    attendance.total_time = total_time_str

                    total_undertime_seconds = 0

                    if shift.period_type == 'Dual':
                        if am_in and am_in > shift.am_in:
                            total_undertime_seconds += (dt.combine(current_date, am_in) - dt.combine(current_date, shift.am_in)).seconds
                        if am_out and am_out < shift.am_out:
                            total_undertime_seconds += (dt.combine(current_date, shift.am_out) - dt.combine(current_date, am_out)).seconds
                        if pm_in and pm_in > shift.pm_in:
                            total_undertime_seconds += (dt.combine(current_date, pm_in) - dt.combine(current_date, shift.pm_in)).seconds
                        if pm_out and pm_out < shift.pm_out:
                            total_undertime_seconds += (dt.combine(current_date, shift.pm_out) - dt.combine(current_date, pm_out)).seconds

                    else:
                        if am_in and am_in > shift.am_in:
                            total_undertime_seconds += (dt.combine(current_date, am_in) - dt.combine(current_date, shift.am_in)).seconds
                        if pm_out and pm_out < shift.pm_out:
                            total_undertime_seconds += (dt.combine(current_date, shift.pm_out) - dt.combine(current_date, pm_out)).seconds

                    total_undertime_hours = total_undertime_seconds // 3600
                    total_undertime_minutes = (total_undertime_seconds % 3600) // 60
                    total_undertime_str = f"{total_undertime_hours}:{total_undertime_minutes:02d}"
                    attendance.total_under_time = total_undertime_str

                    attendance.save()
                    current_date += timedelta(days=1)

            data['form_is_valid'] = True
            dtr = Attendance.objects.all()
            data['attendance_list'] = render_to_string('attkeeper/dtr/dtr_list.html', {'dtr': dtr})

    else:
        form = GenerateDTRForm()

    available_years = AttendanceRecord.objects.dates('date', 'year').distinct()
    years = [year.year for year in available_years]
    months = [{'num': i, 'name': calendar.month_name[i]} for i in range(1, 13)]

    context = {
        'form': form,
        'years': years,
        'months': months,
    }
    data['html_form'] = render_to_string('attkeeper/dtr/generate_dtr.html', context, request=request)
    return JsonResponse(data)


def delete_all_dtr(request):
        data = dict()
        if request.method == 'POST':
            Attendance.objects.all().delete()
            data['form_is_valid'] = True
            dtr = Attendance.objects.all()
            data['attendance_list'] = render_to_string('attkeeper/dtr/dtr_list.html', {'dtr': dtr})
        else:    
            data['html_form'] = render_to_string('attkeeper/dtr/delete_all.html',request=request)
        return JsonResponse(data)


#///////////////////////////////////////

#attendance record//////////////////////

@login_required
def attendance_record(request):
    records = AttendanceRecord.objects.all()
    if(request.method == 'POST'):
        if 'deleteRecord' in request.POST:
            AttendanceRecord.objects.all().delete()
            return redirect('records')
    context = {
        'parent': '',
        'segment': 'records',
        'records': records,
    }

    return render(request, 'attkeeper/attendance_record/record.html',context)

#///////////////////////////////////////

#shift//////////////////////////////////


@login_required
def shift(request):
    shifts = Shift.objects.all()

    context = {
        'parent': '',
        'segment': 'shifts',
        'shifts': shifts,
    }

    return render(request, 'attkeeper/shift/shift.html',context)

def add_shift(request):
        if(request.method == 'POST'):
                form = ShiftForm(request.POST)
        else:    
                form = ShiftForm()

        return save_shift(request, form, 'attkeeper/shift/add_shift.html')


def edit_shift(request,pk):
        shift = get_object_or_404(Shift, pk=pk)
        if(request.method == 'POST'):
                form = ShiftForm(request.POST, instance=shift)
        else:    
                form = ShiftForm(instance=shift)
        return save_shift(request, form, 'attkeeper/shift/edit_shift.html')


def delete_shift(request,pk):
        shift = get_object_or_404(Shift, pk=pk)
        data = dict()
        if request.method == 'POST':
            shift.delete()
            data['form_is_valid'] = True
            shifts= Shift.objects.all()
            data['shift_list'] = render_to_string('attkeeper/shift/shift_list.html',{'shifts':shifts})
        else:    
            context = {'shift':shift}
            data['html_form'] = render_to_string('attkeeper/shift/delete_shift.html',context,request=request)
        return JsonResponse(data)


def save_shift(request, form, template_name):
    data = dict()
    if form.is_valid():
        form.save()
        data['form_is_valid'] = True
        shifts= Shift.objects.all()
        data['shift_list'] = render_to_string('attkeeper/shift/shift_list.html',{'shifts':shifts})
    else:
        data['form_is_valid'] = False

    context = {'form':form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)

#////////////////////////////////////////

#member//////////////////////////////////

@login_required
def member(request):
    members = Member.objects.all()

    context = {
        'parent': '',
        'segment': 'members',
        'members': members,
    }

    return render(request, 'attkeeper/member/member.html',context)

def add_member(request):
        if(request.method == 'POST'):
                form = MemberForm(request.POST)
        else:    
                form = MemberForm()

        return save_member(request, form, 'attkeeper/member/add_member.html')


def edit_member(request,pk):
        member = get_object_or_404(Member, pk=pk)
        if(request.method == 'POST'):
                form = MemberForm(request.POST, instance=member)
        else:    
                form = MemberForm(instance=member)
        return save_member(request, form, 'attkeeper/member/edit_member.html')


def delete_member(request,pk):
        member = get_object_or_404(Member, pk=pk)
        data = dict()
        if request.method == 'POST':
            member.delete()
            data['form_is_valid'] = True
            members= Member.objects.all()
            data['member_list'] = render_to_string('attkeeper/member/member_list.html',{'members':members})
        else:    
            context = {'member':member}
            data['html_form'] = render_to_string('attkeeper/member/delete_member.html',context,request=request)
        return JsonResponse(data)


def save_member(request, form, template_name):
    data = dict()
    if form.is_valid():
        form.save()
        data['form_is_valid'] = True
        members= Member.objects.all()
        data['member_list'] = render_to_string('attkeeper/member/member_list.html',{'members':members})
    else:
        data['form_is_valid'] = False

    context = {'form':form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


def add_position(request):
    if request.method == 'POST':
        form = PositionForm(request.POST)
    else:
        form = PositionForm()

    return save_position(request, form, 'attkeeper/position/add_position.html')

def edit_position(request, pk):
    position = get_object_or_404(Position, pk=pk)
    if request.method == 'POST':
        form = PositionForm(request.POST, instance=position)
    else:
        form = PositionForm(instance=position)
    return save_position(request, form, 'attkeeper/position/edit_position.html')

def delete_position(request, pk):
    position = get_object_or_404(Position, pk=pk)
    data = dict()
    if request.method == 'POST':
        position.delete()
        data['form_is_valid'] = True
        positions = Position.objects.all()
        data['position_list'] = render_to_string('attkeeper/position/position_list.html', {'positions': positions})
    else:
        context = {'position': position}
        data['html_form'] = render_to_string('attkeeper/position/delete_position.html', context, request=request)
    return JsonResponse(data)

def save_position(request, form, template_name):
    data = dict()
    if form.is_valid():
        form.save()
        data['form_is_valid'] = True
        positions = Position.objects.all()
        data['position_list'] = render_to_string('attkeeper/position/position_list.html', {'positions': positions})
    else:
        data['form_is_valid'] = False

    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


@login_required
def branch(request):
    positions = Position.objects.all()
    branches = Branch.objects.all()

    context = {
        'parent': '',
        'segment': 'branches',
        'positions':positions,
        'branches': branches,
    }

    return render(request, 'attkeeper/branch/branch.html', context)

def add_branch(request):
    if request.method == 'POST':
        form = BranchForm(request.POST)
    else:
        form = BranchForm()

    return save_branch(request, form, 'attkeeper/branch/add_branch.html')

def edit_branch(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
    else:
        form = BranchForm(instance=branch)
    return save_branch(request, form, 'attkeeper/branch/edit_branch.html')

def delete_branch(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    data = dict()
    if request.method == 'POST':
        branch.delete()
        data['form_is_valid'] = True
        branches = Branch.objects.all()
        data['branch_list'] = render_to_string('attkeeper/branch/branch_list.html', {'branches': branches})
    else:
        context = {'branch': branch}
        data['html_form'] = render_to_string('attkeeper/branch/delete_branch.html', context, request=request)
    return JsonResponse(data)

def save_branch(request, form, template_name):
    data = dict()
    if form.is_valid():
        form.save()
        data['form_is_valid'] = True
        branches = Branch.objects.all()
        data['branch_list'] = render_to_string('attkeeper/branch/branch_list.html', {'branches': branches})
    else:
        data['form_is_valid'] = False

    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


#////////////////////////////////////////////

#preference//////////////////////////////////

@login_required
def preference(request):
    preference = get_object_or_404(Preference, id=1)  # Adjust the id as necessary
    if request.method == 'POST':
        preference_form = PreferenceForm(request.POST, request.FILES, instance=preference)
        if preference_form.is_valid():
            preference_form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'form_is_valid': True})
            else:
                messages.success(request, 'Preferences updated successfully!')
                return redirect('some_view')  # Adjust the redirect as necessary
    else:
        preference_form = PreferenceForm(instance=preference)

    context = {
        'preference_form': preference_form,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html_form = render_to_string('attkeeper/preference/preference.html', context, request=request)
        return JsonResponse({'html_form': html_form})

    return render(request, 'attkeeper/preference/preference.html', context)

#////////////////////////////////////////////////

#update account//////////////////////////////////
@login_required
def update_account(request):
    if request.method == 'POST':
        form = AccountUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your account was successfully updated!')
            return JsonResponse({'form_is_valid': True})
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = AccountUpdateForm(instance=request.user)

    context = {
        'form': form,
    }
    html_form = render_to_string('accounts/update_account.html', context, request=request)
    return JsonResponse({'form_is_valid': False, 'html_form': html_form})

#/////////////////////////////////////////////

#dtr//////////////////////////////////////////

@login_required
def dtr(request):
    member_id = request.GET.get('member')
    selected_year = int(request.GET.get('year', dt.now().year))
    selected_month = int(request.GET.get('month', dt.now().month))
    selected_start_day = int(request.GET.get('start_day', 1))
    selected_end_day = int(request.GET.get('end_day', calendar.monthrange(selected_year, selected_month)[1]))

    # Adjust the selected_end_day to be within the valid range for the selected month
    _, last_day_of_month = calendar.monthrange(selected_year, selected_month)
    if selected_end_day > last_day_of_month:
        selected_end_day = last_day_of_month

    # Create the start and end dates for the range
    start_date = timezone.make_aware(dt.combine(date(selected_year, selected_month, selected_start_day), dt.min.time()))
    end_date = timezone.make_aware(dt.combine(date(selected_year, selected_month, selected_end_day), dt.max.time()))

    # Filter DTR based on selected values and sort by date
    dtr_records = Attendance.objects.filter(date__range=(start_date, end_date)).order_by('date')
    if member_id:
        dtr_records = dtr_records.filter(member__id=member_id)

    branches = Branch.objects.all()
    members = Member.objects.all()
    if member_id:
        members = members.filter(id=member_id)

    selected_branch_id = None

    if member_id:
        selected_member = members.filter(id=member_id).first()
        if selected_member:
            selected_branch_id = selected_member.branch.id
            members = members.filter(branch__id=selected_branch_id)
            branches = branches.filter(id=selected_branch_id)
    else:
        selected_branch_id = request.GET.get('branch')
        if selected_branch_id and selected_branch_id != "all":
            members = members.filter(branch__id=selected_branch_id)
            branches = branches.filter(id=selected_branch_id)


    # Calculate total time and total undertime for each member
    total_times = {}
    total_undertimes = {}
    days_on_duty = {}

    for member in members:
        member_dtr = dtr_records.filter(member=member)
        total_time_seconds = 0
        total_undertime_seconds = 0

        for record in member_dtr:
            if record.total_time:
                try:
                    hours, minutes = map(int, record.total_time.split(':'))
                    total_time_seconds += hours * 3600 + minutes * 60
                except ValueError:
                    print(f"Error parsing total_time: {record.total_time}")

            if record.total_under_time:
                try:
                    under_hours, under_minutes = map(int, record.total_under_time.split(':'))
                    total_undertime_seconds += under_hours * 3600 + under_minutes * 60
                except ValueError:
                    print(f"Error parsing total_under_time: {record.total_under_time}")

        total_time = timedelta(seconds=total_time_seconds)
        total_undertime = timedelta(seconds=total_undertime_seconds)

        total_time_hours = total_time.total_seconds() // 3600
        total_time_minutes = (total_time.total_seconds() % 3600) // 60

        total_undertime_hours = total_undertime.total_seconds() // 3600
        total_undertime_minutes = (total_undertime.total_seconds() % 3600) // 60

        total_time_str = f"{int(total_time_hours)}:{int(total_time_minutes):02d}"
        total_undertime_str = f"{int(total_undertime_hours)}:{int(total_undertime_minutes):02d}"

        total_times[member.id] = total_time_str
        total_undertimes[member.id] = total_undertime_str
        days_on_duty[member.id] = Attendance.count_on_duty_days(member, start_date, end_date)

    available_years = Attendance.objects.dates('date', 'year').distinct() or []
    years = [year.year for year in available_years]
    months = [{'num': i, 'name': calendar.month_name[i]} for i in range(1, 13)]
    days = list(range(1, 32))
    branches = Branch.objects.all()

    context = {
        'parent': '',
        'segment': 'dtr',
        'dtr': dtr_records,
        'members': members,
        'years': years,
        'months': months,
        'days': days,
        'current_year': selected_year,
        'current_month': selected_month,
        'first_day': selected_start_day,
        'last_day': selected_end_day,
        'selected_member_id': member_id,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'selected_start_day': selected_start_day,
        'selected_end_day': selected_end_day,
        'total_times': total_times,
        'total_undertimes': total_undertimes,
        'days_on_duty': days_on_duty,
        'branches': branches,
        'selected_branch_id': selected_branch_id,
    }

    return render(request, 'attkeeper/dtr/dtr.html', context)

#///////////////////////////////////////

#attendance record//////////////////////


@login_required
def attendance_record(request):
    # if(request.method == 'POST'):
    #     if 'deleteRecord' in request.POST:
    #         AttendanceRecord.objects.all().delete()
    #         return redirect('records')
    branches = Branch.objects.all()
    members = Member.objects.all()
    years = range(2020, dt.now().year + 1)
    months = [
        {'num': i, 'name': dt(2000, i, 1).strftime('%B')}
        for i in range(1, 13)
    ]
    days = range(1, 32)

    branches = Branch.objects.all()
    members = Member.objects.all()
    years = range(2020, dt.now().year + 1)
    months = [
        {'num': i, 'name': dt(2000, i, 1).strftime('%B')}
        for i in range(1, 13)
    ]
    days = range(1, 32)

    selected_branch_id = request.GET.get('branch', 'all')
    selected_member_id = request.GET.get('member', '')
    selected_year = int(request.GET.get('year', dt.now().year))
    selected_month = int(request.GET.get('month', dt.now().month))
    selected_start_day = int(request.GET.get('start_day', 1))
    selected_end_day = int(request.GET.get('end_day', calendar.monthrange(selected_year, selected_month)[1]))

    # Adjust the selected_end_day to be within the valid range for the selected month
    _, last_day_of_month = calendar.monthrange(selected_year, selected_month)
    if selected_end_day > last_day_of_month:
        selected_end_day = last_day_of_month

    start_date = timezone.make_aware(dt.combine(date(selected_year, selected_month, selected_start_day), dt.min.time()))
    end_date = timezone.make_aware(dt.combine(date(selected_year, selected_month, selected_end_day), dt.max.time()))

    # Filter the attendance records by date range
    filtered_records = AttendanceRecord.objects.filter(
        date__range=(start_date, end_date)
    ).order_by('date')
    # Filter Members whose biometric_id does not exist in AttendanceRecord
    members_without_attendance = Member.objects.exclude(
        biometric_id__in=filtered_records.values_list('user_id', flat=True)
    )

    # Filter AttendanceRecords whose user_id does not exist in Member
    attendance_without_members = filtered_records.exclude(
        user_id__in=Member.objects.values_list('biometric_id', flat=True)
    )

    if selected_member_id:
        members = members.filter(id=selected_member_id)

    selected_branch_id = None

    if selected_member_id:
        selected_member = members.filter(id=selected_member_id).first()
        if selected_member:
            selected_branch_id = selected_member.branch.id
            members = members.filter(branch__id=selected_branch_id)
    else:
        selected_branch_id = request.GET.get('branch')
        if selected_branch_id and selected_branch_id != "all":
            members = members.filter(branch__id=selected_branch_id)


    context = {
        'parent': '',
        'segment': 'records',
        'branches': branches,
        'members': members,
        'years': years,
        'months': months,
        'days': days,
        'selected_branch_id': selected_branch_id,
        'selected_member_id': selected_member_id,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'selected_start_day': selected_start_day,
        'selected_end_day': selected_end_day,
        'records': filtered_records,
        'members_without_attendance':members_without_attendance,
        'attendance_without_members':attendance_without_members,


    }

    return render(request, 'attkeeper/attendance_record/record.html',context)

        