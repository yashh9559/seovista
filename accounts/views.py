from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from projects.models import Project
from analyzer.models import SEOReport

#--------------------------------------------------
#REGISTER
#--------------------------------------------------

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Validation
        if not username or not password:
            messages.error(request, "All fields are required")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # Auto login after registration
        login(request, user)
        request.session.set_expiry(1209600)  # 2 weeks

        messages.success(request, "Account created successfully!")
        return redirect('dashboard')

    return render(request, 'register.html')

#---------------------------------------------------
#LOGIN (WITH REMEMBER ME)
#---------------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')

        if not username or not password:
            messages.error(request, "Please enter username and password")
            return redirect('login')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Remember Me logic
            if remember_me:
                request.session.set_expiry(1209600)  # 2 weeks
            else:
                request.session.set_expiry(0)  # logout on browser close

            messages.success(request, "Login successful")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password")
            return redirect('login')

    return render(request, 'login.html')

#---------------------------------------------------
#LOGOUT
#---------------------------------------------------

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully")
    return redirect('login')

# ---------------------------------------------------
# DASHBOARD
# ---------------------------------------------------

@login_required
def dashboard_view(request):
    projects = Project.objects.filter(user=request.user)
    project_data = []

    for project in projects:
        latest_report = SEOReport.objects.filter(
            project=project
        ).order_by('-id').first()

        project_data.append({
            "project": project,
            "latest_report": latest_report
        })

    return render(request, 'dashboard.html', {
        "project_data": project_data
    })