from django.contrib import admin
from django.urls import path, include
from analyzer import views
from django.contrib.auth.views import LogoutView, LoginView
from accounts import views as account_views   # <-- ADD THIS

urlpatterns = [

    path('admin/', admin.site.urls),

    path('', views.home, name='home'),

    path('about/', views.about, name='about'),

    path('contact/', views.contact_view, name='contact'),

    path('dashboard/', views.dashboard, name='dashboard'),

    path('add-project/', views.add_project, name='add_project'),

    path('delete/<int:project_id>/', views.delete_project, name='delete_project'),

    # AUTH ROUTES
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),

    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),

    path('register/', account_views.register_view, name='register'),  # <-- ADD THIS

    # APP ROUTES
    path('', include('analyzer.urls')),
]   