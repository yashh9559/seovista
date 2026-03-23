import requests
import threading
import base64

from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import close_old_connections
from django.http import JsonResponse
from django.core.mail import send_mail

from projects.models import Project
from .models import SEOReport

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ---------------------------------------------------
# BASIC PAGES
# ---------------------------------------------------

def home(request):
    return render(request, "home.html")


def about(request):
    return render(request, "about.html")


# ---------------------------------------------------
# DASHBOARD
# ---------------------------------------------------

@login_required
def dashboard(request):

    projects = Project.objects.filter(user=request.user)

    project_data = []

    for project in projects:

        latest_report = SEOReport.objects.filter(
            project=project
        ).order_by("-id").first()

        project_data.append({
            "project": project,
            "latest_report": latest_report
        })

    return render(request, "dashboard.html", {
        "project_data": project_data
    })


# ---------------------------------------------------
# ADD PROJECT
# ---------------------------------------------------

@login_required
def add_project(request):

    if request.method == "POST":

        website_url = request.POST.get("website_url")

        if website_url:

            website_url = website_url.strip().rstrip("/")

            # prevent duplicate projects
            if not Project.objects.filter(
                website_url=website_url,
                user=request.user
            ).exists():

                Project.objects.create(
                    website_url=website_url,
                    user=request.user
                )

        return redirect("dashboard")

    return render(request, "add_project.html")


# ---------------------------------------------------
# DELETE PROJECT
# ---------------------------------------------------

@login_required
def delete_project(request, project_id):

    project = get_object_or_404(Project, id=project_id, user=request.user)

    project.delete()

    return redirect("dashboard")


# ---------------------------------------------------
# GENERATE SCREENSHOT (FIXED + FALLBACK)
# ---------------------------------------------------

def generate_screenshot(url):

    try:
        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )

            page = browser.new_page()

            page.goto(url, timeout=60000)

            screenshot_bytes = page.screenshot(full_page=True)

            browser.close()

            encoded = base64.b64encode(screenshot_bytes).decode()

            return encoded

    except Exception as e:

        print("Playwright screenshot failed:", e)

        # 🔥 FALLBACK (100% reliable)
        try:
            fallback_url = f"https://image.thum.io/get/fullpage/{url}"
            return fallback_url  # return URL instead of base64
        except:
            return None

# ---------------------------------------------------
# BACKGROUND CRAWLER
# ---------------------------------------------------

def run_crawler(project_id, report_id):

    close_old_connections()

    try:

        project = Project.objects.get(id=project_id)
        report = SEOReport.objects.get(id=report_id)

        base_url = project.website_url.rstrip("/")

        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc

        visited = set()
        to_visit = [base_url]

        max_pages = 10
        max_workers = 5

        pages_crawled = 0
        total_h1 = 0
        total_missing_alt = 0

        crawl_map = []
        issues = []

        headers = {"User-Agent": "Mozilla/5.0"}

        print("Crawler started:", base_url)

        # ---------------- PAGE CRAWLER ----------------

        def crawl_page(url):

            nonlocal pages_crawled, total_h1, total_missing_alt

            try:

                response = requests.get(
                    url,
                    timeout=6,
                    headers=headers,
                    verify=False
                )

            except:
                return []

            if "text/html" not in response.headers.get("Content-Type", ""):
                return []

            soup = BeautifulSoup(response.text, "html.parser")

            # TITLE CHECK
            title_tag = soup.find("title")

            if title_tag:

                title_text = title_tag.get_text().strip()

                if len(title_text) < 30:
                    issues.append(f"Title too short on {url}")

                if len(title_text) > 60:
                    issues.append(f"Title too long on {url}")

            else:
                issues.append(f"Missing title tag on {url}")

            # META DESCRIPTION
            meta_desc = soup.find("meta", attrs={"name": "description"})

            if meta_desc and meta_desc.get("content"):

                desc_text = meta_desc.get("content").strip()

                if len(desc_text) < 120:
                    issues.append(f"Meta description too short on {url}")

                if len(desc_text) > 160:
                    issues.append(f"Meta description too long on {url}")

            else:
                issues.append(f"Missing meta description on {url}")

            # H1 CHECK
            h1_tags = soup.find_all("h1")
            total_h1 += len(h1_tags)

            # IMAGE ALT CHECK
            images = soup.find_all("img")

            missing_alt = [img for img in images if not img.get("alt")]

            total_missing_alt += len(missing_alt)

            if url not in crawl_map:
                crawl_map.append(url)

            discovered_links = []

            for link in soup.find_all("a", href=True):

                full_url = urljoin(url, link["href"])

                parsed_full = urlparse(full_url)

                if parsed_full.netloc != base_domain:
                    continue

                clean_url = full_url.split("#")[0].rstrip("/")

                discovered_links.append(clean_url)

            pages_crawled += 1

            return discovered_links


        # ---------------- PARALLEL CRAWLING ----------------

        with ThreadPoolExecutor(max_workers=max_workers) as executor:

            while to_visit and pages_crawled < max_pages:

                batch = []

                while (
                    to_visit
                    and len(batch) < max_workers
                    and pages_crawled + len(batch) < max_pages
                ):

                    url = to_visit.pop(0)

                    if url not in visited:

                        visited.add(url)
                        batch.append(url)

                results = executor.map(crawl_page, batch)

                for links in results:

                    for link in links:

                        if link not in visited and link not in to_visit:
                            to_visit.append(link)


        # ---------------- ROBOTS / SITEMAP ----------------

        try:
            robots_found = requests.get(
                f"{base_url}/robots.txt",
                timeout=3
            ).status_code == 200
        except:
            robots_found = False

        try:
            sitemap_found = requests.get(
                f"{base_url}/sitemap.xml",
                timeout=3
            ).status_code == 200
        except:
            sitemap_found = False


        # ---------------- SEO SCORE ----------------

        score = 100

        if total_missing_alt > 0:
            score -= min(total_missing_alt, 30)

        if total_h1 == 0:
            score -= 20

        if robots_found:
            score += 5

        if sitemap_found:
            score += 5

        score = max(0, min(score, 100))


        # ---------------- SAVE REPORT ----------------

        report.refresh_from_db()

        report.h1_count = total_h1
        report.missing_alt_count = total_missing_alt
        report.pages_crawled = pages_crawled
        report.score = score

        report.issues = "\n".join(set(issues))
        report.crawl_map = "\n".join(crawl_map)

        report.status = "Completed"

        report.save()

        print("Crawler finished successfully")

    except Exception as e:

        print("Crawler error:", e)

        try:

            report = SEOReport.objects.get(id=report_id)

            report.status = "Failed"

            report.save(update_fields=["status"])

        except:
            pass


# ---------------------------------------------------
# START ANALYSIS
# ---------------------------------------------------

@login_required
def analyze_project(request, project_id):

    project = get_object_or_404(Project, id=project_id, user=request.user)

    report = SEOReport.objects.create(
        project=project,
        status="Running"
    )

    thread = threading.Thread(
        target=run_crawler,
        args=(project.id, report.id),
        daemon=True
    )

    thread.start()

    return redirect("dashboard")


# ---------------------------------------------------
# REPORT HISTORY
# ---------------------------------------------------

@login_required
def report_history(request, project_id):

    project = get_object_or_404(Project, id=project_id, user=request.user)

    reports = SEOReport.objects.filter(
        project=project
    ).order_by("-analyzed_at")

    return render(request, "report_history.html", {
        "project": project,
        "reports": reports
    })


# ---------------------------------------------------
# STATUS CHECK
# ---------------------------------------------------

@login_required
def check_report_status(request, project_id):

    latest_report = SEOReport.objects.filter(
        project_id=project_id
    ).order_by("-id").first()

    if not latest_report:

        return JsonResponse({"status": "None"})

    return JsonResponse({
        "status": latest_report.status,
        "score": latest_report.score,
        "pages": latest_report.pages_crawled
    })


# ---------------------------------------------------
# CONTACT FORM
# ---------------------------------------------------

def contact_view(request):

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        message = request.POST.get("message")

        send_mail(
            f"New Contact Message from {name}",
            message,
            email,
            ['sawantyash9559@gmail.com'],
        )

    return render(request, "contact.html")