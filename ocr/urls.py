"""project URL Configuration

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
from django.conf.urls import url
from django.contrib import admin
from core import views as core_views
from django.conf.urls import url, include
from django.views.generic import RedirectView


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    # url(r'^api-auth/', include('rest_framework.urls')),
    url(r'^$', core_views.Home.as_view()),

    url(r'^login/', core_views.Login.as_view()),
    url(r'accounts/login/', RedirectView.as_view(url='/')),
    url(r'^check_login/', core_views.CheckLogin.as_view()),
    url(r'^logout/', core_views.Logout.as_view()),

    url(r'^ocr/', core_views.OCR.as_view()),
    url(r'^api/ocr/', core_views.OcrAPI.as_view()),

    url(r'file/*', core_views.RetrieveFiles.as_view()),
]
