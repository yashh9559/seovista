from django.db import models
from projects.models import Project


class SEOReport(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)

    title = models.TextField(null=True, blank=True)
    meta_description = models.TextField(null=True, blank=True)

    h1_count = models.IntegerField(default=0)
    missing_alt_count = models.IntegerField(default=0)
    score = models.IntegerField(default=0)

    robots_txt_found = models.BooleanField(default=False)
    sitemap_found = models.BooleanField(default=False)

    has_hsts = models.BooleanField(default=False)
    has_csp = models.BooleanField(default=False)
    has_x_frame = models.BooleanField(default=False)

    pages_crawled = models.IntegerField(default=0)   # <-- ADD THIS

    status = models.CharField(max_length=20, default="Completed")
    analyzed_at = models.DateTimeField(auto_now_add=True)
    
    issues = models.TextField(blank=True, null=True)
    crawl_map = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.project.website_url} - {self.status}"

