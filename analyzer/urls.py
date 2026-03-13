from django.urls import path
from . import views

urlpatterns = [

    path('analyze/<int:project_id>/', views.analyze_project, name='analyze_project'),

    path('reports/<int:project_id>/', views.report_history, name='report_history'),

    path('status/<int:project_id>/', views.check_report_status, name='check_report_status'),


]