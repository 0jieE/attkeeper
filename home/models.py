from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from datetime import datetime as dt, timedelta
from django.utils import timezone
from django.db.models import Q

class AccountManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_admin') is not True:
            raise ValueError('Superuser must have is_admin=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, password, **extra_fields)

class Account(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=255, unique=True)
    is_staff = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_member = models.BooleanField(default=False)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    objects = AccountManager()

    def __str__(self):
        return self.username


class Shift(models.Model):
    DUAL = 'Dual'
    SINGLE = 'Single'
    TYPE = ((SINGLE,'Single'),
            (DUAL,'Dual'),)
    shift_name = models.CharField(max_length=255)
    period_type = models.CharField(max_length=20, choices=TYPE, default=DUAL)
    hours = models.IntegerField()
    am_in = models.TimeField(null=True, blank=True)
    am_out = models.TimeField(null=True, blank=True)
    pm_in_start_time = models.TimeField(null=True, blank=True)
    pm_in = models.TimeField(null=True, blank=True)
    pm_out = models.TimeField(null=True, blank=True)

    def __str__(self):
        return self.shift_name
    
class Position(models.Model):
    position_name = models.CharField(max_length=50)

    def __str__(self):
        return self.position_name
    
class Branch(models.Model):
    branch_name = models.CharField(max_length=255)
    signatory = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.branch_name}"


class Member(models.Model):
    biometric_id = models.IntegerField()
    last_name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255)
    middle_name = models.CharField(max_length=255, blank=True, null=True)
    ext_name = models.CharField(max_length=255, blank=True, null=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    position = models.ForeignKey(Position, on_delete=models.CASCADE)
    address = models.TextField()
    contact_no = models.CharField(max_length=20, blank=True, null=True)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.last_name}, {self.first_name} {self.middle_name or ''} {self.ext_name or ''}".strip()

class Period(models.Model):
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    description = models.TextField()

    def __str__(self):
        return f"From {self.start_date} to {self.end_date}"


class Attendance(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    period = models.ForeignKey(Period, on_delete=models.CASCADE)
    date = models.DateField()
    days = models.CharField(max_length=255)
    am_in = models.CharField(max_length=255, blank=True, null=True)
    am_out = models.CharField(max_length=255, blank=True, null=True)
    pm_in = models.CharField(max_length=255, blank=True, null=True)
    pm_out = models.CharField(max_length=255, blank=True, null=True)
    total_time = models.CharField(max_length=255, blank=True, null=True)
    total_under_time = models.CharField(max_length=255, blank=True, null=True)

    def calculate_total_time_and_undertime(self):
        shift = self.member.shift
        total_time_seconds = 0
        total_undertime_seconds = 0

        am_in = dt.strptime(self.am_in, '%I:%M %p') if self.am_in else None
        am_out = dt.strptime(self.am_out, '%I:%M %p') if self.am_out else None
        pm_in = dt.strptime(self.pm_in, '%I:%M %p') if self.pm_in else None
        pm_out = dt.strptime(self.pm_out, '%I:%M %p') if self.pm_out else None

        shift_am_in = timezone.make_aware(dt.combine(self.date, shift.am_in)) if shift.am_in else None
        shift_am_out = timezone.make_aware(dt.combine(self.date, shift.am_out)) if shift.am_out else None
        shift_pm_in = timezone.make_aware(dt.combine(self.date, shift.pm_in)) if shift.pm_in else None
        shift_pm_out = timezone.make_aware(dt.combine(self.date, shift.pm_out)) if shift.pm_out else None

        if am_in:
            am_in_time = timezone.make_aware(dt.combine(self.date, am_in.time()))
        if am_out:
            am_out_time = timezone.make_aware(dt.combine(self.date, am_out.time()))
        if pm_in:
            pm_in_time = timezone.make_aware(dt.combine(self.date, pm_in.time()))
        if pm_out:
            pm_out_time = timezone.make_aware(dt.combine(self.date, pm_out.time()))

        if shift.period_type == 'Dual' :
            if am_in and am_out:
                if am_in_time > shift_am_in and am_out_time < shift_am_out:
                    total_time_seconds += (am_out_time - am_in_time).seconds
                elif am_in_time > shift_am_in:
                    total_time_seconds += (shift_am_out - am_in_time).seconds
                elif am_out_time < shift_am_out:
                    total_time_seconds += (am_out_time - shift_am_in).seconds
                else:
                    total_time_seconds += (shift_am_out - shift_am_in).seconds

            if pm_in and pm_out:
                if pm_in_time > shift_pm_in and pm_out_time < shift_pm_out:
                    total_time_seconds += (pm_out_time - pm_in_time).seconds
                elif pm_in_time > shift_pm_in:
                    total_time_seconds += (shift_pm_out - pm_in_time).seconds
                elif pm_out_time < shift_pm_out:
                    total_time_seconds += (pm_out_time - shift_pm_in).seconds
                else:
                    total_time_seconds += (shift_pm_out - shift_pm_in).seconds
        else:
            if am_in and pm_out:
                if am_in_time > shift_am_in and pm_out_time < shift_pm_out:
                    total_time_seconds += (pm_out_time - am_in_time).seconds
                elif am_in_time > shift_am_in:
                    total_time_seconds += (shift_pm_out - am_in_time).seconds
                elif pm_out_time < shift_pm_out:
                    total_time_seconds += (pm_out_time - shift_am_in).seconds
                else:
                    total_time_seconds += (shift_pm_out - shift_am_in).seconds

        total_time_hours = total_time_seconds // 3600
        total_time_minutes = (total_time_seconds % 3600) // 60
        self.total_time = f"{total_time_hours}:{total_time_minutes:02d}"

        if shift.period_type == 'Dual':
            if am_in and am_in_time > shift_am_in:
                total_undertime_seconds += (am_in_time - shift_am_in).seconds
            if am_out and am_out_time < shift_am_out:
                total_undertime_seconds += (shift_am_out - am_out_time).seconds
            if pm_in and pm_in_time > shift_pm_in:
                total_undertime_seconds += (pm_in_time - shift_pm_in).seconds
            if pm_out and pm_out_time < shift_pm_out:
                total_undertime_seconds += (shift_pm_out - pm_out_time).seconds
        else:
            if am_in and am_in_time > shift_am_in:
                total_undertime_seconds += (am_in_time - shift_am_in).seconds
            if pm_out and pm_out_time < shift_pm_out:
                total_undertime_seconds += (shift_pm_out - pm_out_time).seconds

        total_undertime_hours = total_undertime_seconds // 3600
        total_undertime_minutes = (total_undertime_seconds % 3600) // 60
        self.total_under_time = f"{total_undertime_hours}:{total_undertime_minutes:02d}"

    @classmethod
    def count_on_duty_days(cls, member, start_date, end_date):
        attendances = cls.objects.filter(member=member, date__range=(start_date, end_date))

        if member.shift.period_type == 'Dual':
            on_duty_days = attendances.filter(
                (Q(am_in__isnull=False) & Q(am_out__isnull=False)) |
                (Q(pm_in__isnull=False) & Q(pm_out__isnull=False))
            ).values('date').distinct().count()
        else:  # Single period type
            on_duty_days = attendances.filter(
                Q(am_in__isnull=False) & Q(pm_out__isnull=False)
            ).values('date').distinct().count()

        return on_duty_days
    
    def save(self, *args, **kwargs):
        self.calculate_total_time_and_undertime()
        super(Attendance, self).save(*args, **kwargs)

    def __str__(self):
        return f"Attendance of {self.member}"


class Preference(models.Model):
    logo = models.ImageField(upload_to='logo/', null=True, blank=True)
    company_name = models.CharField(max_length=255,default='Company Name')
    description = models.CharField(max_length=255, default="Description")

    def __str__(self):
        return f"{self.company_name}"


class AttendanceRecord(models.Model):
    user_id = models.IntegerField()
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=50)
    period = models.ForeignKey(Period, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user_id} - {self.date} {self.time} - {self.status}"
    


