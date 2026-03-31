from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from projects.models import Project
from analyzer.models import SEOReport


# ---------------------------------------------------
# REGISTER
# ---------------------------------------------------

def register_view(request):

    if request.method == 'POST':

        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # 🔒 Validation
        if not username or not password:
            messages.error(request, "All fields are required")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')

        # ✅ Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        messages.success(request, "Account created successfully. Please login.")
        return redirect('login')

    return render(request, 'register.html')


# ---------------------------------------------------
# LOGIN (FIXED)
# ---------------------------------------------------

def login_view(request):

    # ✅ If already logged in → skip login page
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')

        # 🔒 Safety check
        if not username or not password:
            messages.error(request, "Please enter username and password")
            return redirect('login')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # 🔥 IMPORTANT (ensures session works)
            request.session.set_expiry(86400)  # 1 day session

            messages.success(request, "Login successful")
            return redirect('dashboard')

        else:
            messages.error(request, "Invalid username or password")
            return redirect('login')

    return render(request, 'login.html')


# ---------------------------------------------------
# LOGOUT (SAFE)
# ---------------------------------------------------

def logout_view(request):

    if request.method == "POST":
        logout(request)
        messages.success(request, "Logged out successfully")
        return redirect('login')

    return redirect('dashboard')


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