from django.urls import path
from . import views

urlpatterns = [
    path('add-project/', views.add_project, name='add_project'),
    path('delete/<int:project_id>/', views.delete_project, name='delete_project'),
]
