
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from myapp import views
from myapp.sitemaps import sitemaps

urlpatterns = [
    path('admin/reports/', views.admin_reports, name='admin_reports'),
    path('admin/reports/businesses.csv', views.admin_business_csv, name='admin_business_csv'),
    path('admin/reports/revenue.csv', views.admin_revenue_csv, name='admin_revenue_csv'),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('healthz/', views.healthz, name='healthz'),
    path('robots.txt', views.robots_txt, name='robots.txt'),

    path('', include('myapp.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
