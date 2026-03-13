from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Project


@login_required
def add_project(request):
    if request.method == 'POST':
        website_url = request.POST['website_url']

        Project.objects.create(
            user=request.user,
            website_url=website_url
        )

        return redirect('dashboard')

    return render(request, 'add_project.html')


from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Project


@login_required
def delete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)

    if request.method == "POST":
        project.delete()
        return redirect("dashboard")

    return redirect("dashboard")

from django.shortcuts import render

def home(request):
    return render(request, 'home.html')

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')