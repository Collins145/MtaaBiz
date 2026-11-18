
from django.contrib import admin
from django.urls import path, include
from myapp import views

urlpatterns = [
    path('admin/reports/', views.admin_reports, name='admin_reports'),
    path('admin/reports/businesses.csv', views.admin_business_csv, name='admin_business_csv'),
    path('admin/reports/revenue.csv', views.admin_revenue_csv, name='admin_revenue_csv'),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),

    path('', include('myapp.urls')),
]
