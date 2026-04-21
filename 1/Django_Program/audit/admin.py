from django.contrib import admin
from .models import Project, Document, Issue

admin.site.register(Project)
admin.site.register(Document)
admin.site.register(Issue)

from django.contrib import admin
from .models import AuditTool

@admin.register(AuditTool)
class AuditToolAdmin(admin.ModelAdmin):
    change_list_template = "admin/audit_tool.html"

    def has_add_permission(self, request):
        return False