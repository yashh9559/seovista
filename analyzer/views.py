import requests
import threading

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import close_old_connections
from django.http import JsonResponse
from django.core.mail import send_mail

from projects.models import Project
from .models import SEOReport

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def home(request):
    return render(request, "home.html")


def about(request):
    return render(request, "about.html")


@login_required
def dashboard(request):
    projects = Project.objects.filter(user=request.user)
    project_data = []

    for project in projects:
        latest_report = SEOReport.objects.filter(project=project).order_by("-id").first()
        project_data.append({
            "project": project,
            "latest_report": latest_report
        })

    return render(request, "dashboard.html", {"project_data": project_data})


@login_required
def add_project(request):
    if request.method == "POST":
        website_url = request.POST.get("website_url")

        if website_url:
            website_url = website_url.strip().rstrip("/")

            if not Project.objects.filter(website_url=website_url, user=request.user).exists():
                Project.objects.create(website_url=website_url, user=request.user)

        return redirect("dashboard")

    return render(request, "add_project.html")


@login_required
def delete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)
    project.delete()
    return redirect("dashboard")


@login_required
def report_history(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)
    reports = SEOReport.objects.filter(project=project).order_by("-id")

    return render(request, "report_history.html", {
        "project": project,
        "reports": reports
    })


# 🔥 SIMPLE + WORKING SCREENSHOT (NO PLAYWRIGHT)
def generate_screenshot(url):
    return f"https://image.thum.io/get/fullpage/{url}"


def run_crawler(project_id, report_id):
    close_old_connections()

    try:
        project = Project.objects.get(id=project_id)
        report = SEOReport.objects.get(id=report_id)

        base_url = project.website_url.rstrip("/")
        domain = urlparse(base_url).netloc

        visited = set()
        to_visit = [base_url]

        pages = 0
        h1_count = 0
        missing_alt = 0

        issues = []
        crawl_map = []

        def crawl(url):
            nonlocal pages, h1_count, missing_alt

            try:
                res = requests.get(url, timeout=5, verify=False)
            except:
                return []

            if "text/html" not in res.headers.get("Content-Type", ""):
                return []

            soup = BeautifulSoup(res.text, "html.parser")

            if not soup.find("title"):
                issues.append(f"Missing title on {url}")

            if not soup.find("meta", attrs={"name": "description"}):
                issues.append(f"Missing meta description on {url}")

            h1_count += len(soup.find_all("h1"))
            missing_alt += len([img for img in soup.find_all("img") if not img.get("alt")])

            crawl_map.append(url)
            pages += 1

            links = []
            for a in soup.find_all("a", href=True):
                full = urljoin(url, a["href"])
                if urlparse(full).netloc == domain:
                    links.append(full.split("#")[0].rstrip("/"))

            return links

        while to_visit and pages < 10:
            url = to_visit.pop(0)

            if url not in visited:
                visited.add(url)
                new_links = crawl(url)

                for link in new_links:
                    if link not in visited:
                        to_visit.append(link)

        score = 100
        if missing_alt > 0:
            score -= min(missing_alt, 30)
        if h1_count == 0:
            score -= 20

        # 🔥 SAVE SCREENSHOT
        report.screenshot = generate_screenshot(base_url)

        report.h1_count = h1_count
        report.missing_alt_count = missing_alt
        report.pages_crawled = pages
        report.score = max(0, min(score, 100))
        report.issues = "\n".join(set(issues))
        report.crawl_map = "\n".join(crawl_map)
        report.status = "Completed"

        report.save()

    except Exception as e:
        print("Crawler error:", e)


@login_required
def analyze_project(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)

    report = SEOReport.objects.create(project=project, status="Running")

    thread = threading.Thread(
        target=run_crawler,
        args=(project.id, report.id),
        daemon=True
    )

    thread.start()

    return redirect("dashboard")


@login_required
def check_report_status(request, project_id):
    report = SEOReport.objects.filter(project_id=project_id).order_by("-id").first()

    if not report:
        return JsonResponse({"status": "None"})

    return JsonResponse({
        "status": report.status,
        "score": report.score,
        "pages": report.pages_crawled
    })


def contact_view(request):
    if request.method == "POST":
        send_mail(
            "Contact Message",
            request.POST.get("message"),
            request.POST.get("email"),
            ["sawantyash9559@gmail.com"],
        )

    return render(request, "contact.html")