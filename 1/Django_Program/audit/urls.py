from .views import upload_and_audit
from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.upload_and_audit, name="upload_and_audit"),
    path("page/", views.upload_page, name="upload_page"),
    path('upload/', upload_and_audit, name='upload_and_audit'),
    path("stream/", views.stream_reasoning, name="stream_reasoning"),
]


