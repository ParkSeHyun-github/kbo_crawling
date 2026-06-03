from django.urls import path
from . import views

urlpatterns = [
    path('', views.batter_list, name='batter_list'),
    path('pitchers/', views.pitcher_list, name='pitcher_list'),
    path('charts/', views.charts, name='charts'),
    path('standings/', views.standings, name='standings'),
    path('predict/', views.predict, name='predict'),
    path('crawl/', views.crawl_start, name='crawl_start'),
    path('crawl/status/', views.crawl_status, name='crawl_status'),
]
