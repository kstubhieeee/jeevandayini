from django.urls import path
from accounts import views as accounts_views

urlpatterns = [
    path('send_certificate/<int:appointment_id>/', accounts_views.send_certificate, name='send_certificate'),
    path('certificate_preview/<int:appointment_id>/', accounts_views.certificate_preview, name='certificate_preview'),
    path('send_certificate_confirm/<int:appointment_id>/', accounts_views.send_certificate_confirm, name='send_certificate_confirm'),
] 