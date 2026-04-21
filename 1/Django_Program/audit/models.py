from django.db import models

class Project(models.Model):
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

class Document(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class Issue(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    issue_type = models.CharField(max_length=100)
    risk_level = models.CharField(max_length=20)
    description = models.TextField()
    status = models.CharField(max_length=20, default='待确认')
    created_at = models.DateTimeField(auto_now_add=True)

class AuditTool(models.Model):
    class Meta:
        verbose_name = "智能审核系统"
        verbose_name_plural = "智能审核系统"



