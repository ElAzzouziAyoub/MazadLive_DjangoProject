"""
URL configuration for MazadLive project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from auctions import template_views as tv

urlpatterns = [
    path('admin/', admin.site.urls),

    # REST API
    path('api/', include('auctions.urls')),
    path('api-auth/', include('rest_framework.urls')),

    # Frontend
    path('', tv.home, name='home'),
    path('auctions/create/', tv.create_auction, name='create_auction'),
    path('auctions/<int:pk>/', tv.auction_detail, name='auction_detail'),
    path('auctions/<int:pk>/bid/', tv.place_bid, name='place_bid'),

    path('watchlist/', tv.watchlist_view, name='watchlist'),
    path('watchlist/add/', tv.watchlist_add, name='watchlist_add'),
    path('watchlist/remove/<int:pk>/', tv.watchlist_remove, name='watchlist_remove'),

    path('my-auctions/', tv.my_auctions, name='my_auctions'),
    path('won/', tv.won_auctions, name='won_auctions'),

    path('login/', tv.login_view, name='login'),
    path('register/', tv.register_view, name='register'),
    path('logout/', tv.logout_view, name='logout'),
]
