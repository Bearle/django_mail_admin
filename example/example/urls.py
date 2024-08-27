"""example URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.urls import path, include, re_path

# from django.conf.urls import url
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

from . import views

urlpatterns = [
    re_path(r"^admin/", admin.site.urls),
    re_path(r"", include("django_mail_admin.urls", namespace="django_mail_admin")),
    path(r"example/mailbox/", views.mailbox, name="mailbox_list"),
    path(
        r"example/mailbox/<int:id>/auth1",
        views.mailbox_auth_step1,
        name="mailbox_auth_step1",
    ),
    path(r"example/mailbox/auth2", views.mailbox_auth_step2, name="mailbox_auth_step2"),
    re_path(r"^example/", include("social_django.urls", namespace="social")),
]
if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
