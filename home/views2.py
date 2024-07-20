from datetime import datetime, timedelta
import calendar
from django.utils.timezone import make_aware
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, authenticate, login
from calendar import monthrange
from django.http import JsonResponse
from django.contrib import messages
from .forms import UploadFileForm, LoginForm
from .models import AttendanceRecord, Shift, Period, Attendance, Member
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date

def process_file(file):
    status_mapping = {
        0: 'check-in',
        1: 'check-out',
        4: 'ot-in',
        5: 'ot-out'
    }

    for line in file:
        data = line.decode('utf-8').strip().split()
        if len(data) >= 6:  # Ensure there are enough elements
            user_id = int(data[0])
            date_str = data[1]
            time_str = data[2]
            status_key = int(data[4])
            status = status_mapping.get(status_key, 'unknown')

            # Convert date and time to appropriate objects
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            time = datetime.strptime(time_str, '%H:%M:%S').time()

            # Determine the first and last day of the month for the period
            first_day_of_month = datetime(date.year, date.month, 1)
            last_day_of_month = datetime(date.year, date.month, monthrange(date.year, date.month)[1])
            
            # Make dates timezone aware
            first_day_of_month = make_aware(first_day_of_month)
            last_day_of_month = make_aware(last_day_of_month)
            
            # Get or create the Period object for the record's date
            period, created = Period.objects.get_or_create(
                start_date=first_day_of_month,
                end_date=last_day_of_month,
                defaults={'description': f"Period for {date.strftime('%B %Y')}"}
            )
            
            # Check for existing record to prevent duplicates
            if not AttendanceRecord.objects.filter(user_id=user_id, date=date, time=time, status=status).exists():
                # Save the data to the AttendanceRecord model
                AttendanceRecord.objects.create(
                    user_id=user_id, 
                    date=date, 
                    time=time, 
                    status=status,
                    period=period  # Associate the record with the created period
                )

@login_required
def upload_file(request):
    data = dict()
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            process_file(request.FILES['file'])
            data['form_is_valid'] = True
            records = AttendanceRecord.objects.all()
            data['record_list'] = render_to_string('attkeeper/attendance_record/record_list.html', {'records': records})
        else:
            data['form_is_valid'] = False
    else:
        form = UploadFileForm()

    context = {'form': form}
    data['html_form'] = render_to_string('attkeeper/attendance_record/upload.html', context, request=request)
    return JsonResponse(data)


@login_required
def fetch_available_times(request):
    date = request.GET.get('date')
    member_id = request.GET.get('member_id')

    # Parse the date string to a date object
    try:
        date_obj = datetime.strptime(date, '%B %d, %Y').date()
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid date format.'})

    member = Member.objects.get(id=member_id)
    attendance_records = AttendanceRecord.objects.filter(user_id=member.biometric_id, date=date_obj)

    # Convert times to 12-hour format
    times = [datetime.strptime(str(record.time), '%H:%M:%S').strftime('%I:%M %p') for record in attendance_records]

    return JsonResponse({'success': True, 'times': times})



@login_required
@csrf_exempt
def update_attendance_time(request):
    if request.method == 'POST':
        date = request.POST.get('date')
        member_id = request.POST.get('member_id')
        time_type = request.POST.get('time_type')
        time = request.POST.get('time')

        try:
            # Parse the date string to a date object
            date_obj = datetime.strptime(date, '%B %d, %Y').date()
            
            # Parse time from 12-hour format with AM/PM to a datetime object
            time_obj = datetime.strptime(time, '%I:%M %p')

            # Find the Attendance record
            attendance = Attendance.objects.get(member_id=member_id, date=date_obj)

            # Update the appropriate time field using strftime to get time in string format
            setattr(attendance, time_type, time_obj.strftime('%I:%M %p'))

            # Save the updated record
            attendance.save()
            return JsonResponse({'success': True})
        
        except Attendance.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Attendance record not found.'})
        except ValueError as e:
            return JsonResponse({'success': False, 'error': f'Invalid data format: {str(e)}'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error updating time: {str(e)}'})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})


@login_required
@csrf_exempt
def remove_attendance_time(request):
    if request.method == 'POST':
        date = request.POST.get('date')
        member_id = request.POST.get('member_id')
        time_type = request.POST.get('time_type')

        try:
            # Parse the date string to a date object
            date_obj = datetime.strptime(date, '%B %d, %Y').date()

            # Find the Attendance record
            attendance = Attendance.objects.get(member_id=member_id, date=date_obj)

            # Remove the appropriate time field
            setattr(attendance, time_type, None)  # Assuming you want to set it to None

            # Save the updated record
            attendance.save()
            return JsonResponse({'success': True})

        except Attendance.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Attendance record not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error removing time: {str(e)}'})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})
