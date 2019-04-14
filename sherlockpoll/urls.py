"""sherlockpoll URL Configuration

"""
import django.conf.urls
from main import views

urlpatterns = [
    django.conf.urls.re_path(r'^$', views.index, name='index'),
    django.conf.urls.re_path(r'^oauthcallback/', views.oauthcallback, name='oauthcallback'),
    django.conf.urls.re_path(r'^interactive_button/', views.interactive_button, name='interactive_button'),
    django.conf.urls.re_path(r'^poll/', views.sherlock_poll, name='poll'),
    django.conf.urls.re_path(r'^privacy-policy/', views.privacy_policy, name='privacy-policy'),
]
