from django.urls import path
from .import views,views2

urlpatterns = [

    path("",views.index,name='index'),

    #Authentication
    path("accounts/login/",views.login_view,name='login'),
    path('accounts/logout/', views.logout_view, name='signout'),

    path('upload/', views2.upload_file, name='upload'),
    path('attendance-record/', views.attendance_record, name='records'),

    path('generate-dtr/', views.generate_attendance, name='generate_dtr'),
    path('delete-dtr/', views.delete_all_dtr, name='delete-dtr'),
    path('dtr/', views.dtr, name='dtr'),
    path('fetch-available-times/', views2.fetch_available_times, name='fetch_available_times'),
    path('update-attendance-time/', views2.update_attendance_time, name='update_attendance_time'),
    path('remove_attendance_time/', views2.remove_attendance_time, name='remove_attendance_time'), 

    path('shifts/', views.shift, name='shifts'),
    path('add-shifts/', views.add_shift, name='add_shift'),
    path('edit-shift/<int:pk>/edit/', views.edit_shift, name='edit_shift'),
    path('delete-shift/<int:pk>/delete/', views.delete_shift, name='delete_shift'),

    path('members/', views.member, name='members'),
    path('add-members/', views.add_member, name='add_member'),
    path('edit-member/<int:pk>/edit/', views.edit_member, name='edit_member'),
    path('delete-member/<int:pk>/delete/', views.delete_member, name='delete_member'),

    path('preferences/', views.preference, name='preference'),
    path('update-account/', views.update_account, name='update_account'),

    path('positions/add/', views.add_position, name='add_position'),
    path('positions/edit/<int:pk>/', views.edit_position, name='edit_position'),
    path('positions/delete/<int:pk>/', views.delete_position, name='delete_position'),
    path('branches/', views.branch, name='branch'),
    path('branches/add/', views.add_branch, name='add_branch'),
    path('branches/edit/<int:pk>/', views.edit_branch, name='edit_branch'),
    path('branches/delete/<int:pk>/', views.delete_branch, name='delete_branch'),
]
