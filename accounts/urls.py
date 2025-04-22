from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import CustomLoginForm

urlpatterns = [
    path('', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('blood-bank/login/', views.blood_bank_login_view, name='blood_bank_login'),
    path('blood-bank/signup/', views.blood_bank_signup_view, name='blood_bank_signup'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('type-donation/', views.type_donation_view, name='type_donation'),
    path('blood-donation-types/', views.blood_donation_types_view, name='blood_donation_types'),
    path('search-camps/', views.search_camps_view, name='search_camps'),
    path('search-banks/', views.search_banks_view, name='search_banks'),
    path('search-banks/results/', views.search_banks, name='search_banks_results'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path('blood-availability/', views.blood_availability_view, name='blood_availability'),
    path('get-blood-availability/', views.get_blood_availability, name='get_blood_availability'),
    path('get-districts/<int:state_id>/', views.get_districts, name='get_districts'),
    path('about/', views.about_view, name='about'),
    path('search-camps/results/', views.search_camps, name='search_camps_results'),
    path('schedule-appointment/<int:bank_id>/', views.schedule_appointment_view, name='schedule_appointment'),
    path('blood-bank/dashboard/', views.blood_bank_dashboard, name='blood_bank_dashboard'),
    path('blood-bank/update-stock/', views.update_blood_stock, name='update_blood_stock'),
    path('blood-bank/add-stock/', views.add_blood_stock, name='add_blood_stock'),
    path('blood-bank/organize-camp/', views.organize_camp, name='organize_camp'),
    path('registered-users/', views.registered_users, name='registered_users'),
    path('appointment-confirmation/', views.appointment_confirmation, name='appointment_confirmation'),
    path('appointment/accept/<int:appointment_id>/', views.accept_appointment, name='accept_appointment'),
    path('appointment/reject/<int:appointment_id>/', views.reject_appointment, name='reject_appointment'),
    path('confirmed-appointments/', views.confirmed_appointments, name='confirmed_appointments'),
    path('appointment/mark-donated/<int:appointment_id>/', views.mark_donated, name='mark_donated'),
    path('appointment/mark-not-donated/<int:appointment_id>/', views.mark_not_donated, name='mark_not_donated'),
    path('appointment/send-certificate/<int:appointment_id>/', views.send_certificate, name='send_certificate'),
    path('view-certificates/', views.view_certificates, name='view_certificates'),
    path('view-certificate/<int:donation_id>/', views.view_certificate_detail, name='view_certificate_detail'),
] 