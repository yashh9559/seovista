from django.contrib import admin
from django.urls import path, include

from analyzer import views
from accounts import views as account_views   # ✅ your custom auth

urlpatterns = [

    path('admin/', admin.site.urls),

    # ---------------- BASIC ----------------
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact_view, name='contact'),

    # ---------------- AUTH (FIXED) ----------------
    path('login/', account_views.login_view, name='login'),
    path('logout/', account_views.logout_view, name='logout'),
    path('register/', account_views.register_view, name='register'),

    # ---------------- DASHBOARD ----------------
    path('dashboard/', views.dashboard, name='dashboard'),

    # ---------------- PROJECT ----------------
    path('add-project/', views.add_project, name='add_project'),
    path('delete/<int:project_id>/', views.delete_project, name='delete_project'),

    # ---------------- ANALYZER ----------------
    path('', include('analyzer.urls')),
]