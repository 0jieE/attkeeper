from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Account, AttendanceRecord, Shift, Member, Period, Attendance, Preference
from .forms import CustomUserCreationForm, CustomUserChangeForm

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = Account
    list_display = ['username','is_superuser', 'is_staff', 'is_admin', 'is_member']
    list_filter = ['is_staff', 'is_admin', 'is_member']
    fieldsets = (
        (None, {'fields': ('username',)}),
        ('Permissions', {'fields': ('is_staff', 'is_admin', 'is_member', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'is_staff', 'is_admin', 'is_member')}
        ),
    )
    search_fields = ('username',)
    ordering = ('username',)

admin.site.register(Account, CustomUserAdmin)
admin.site.register(AttendanceRecord)
admin.site.register(Shift)
admin.site.register(Member)
admin.site.register(Period)
admin.site.register(Attendance)
admin.site.register(Preference)

