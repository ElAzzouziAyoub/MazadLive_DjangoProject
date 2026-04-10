from django.urls import path

from . import views

urlpatterns = [
    # Auctions
    path('auctions/', views.AuctionListCreateView.as_view(), name='auction-list-create'),
    path('auctions/<int:pk>/', views.AuctionDetailView.as_view(), name='auction-detail'),
    path('auctions/<int:pk>/bid/', views.PlaceBidView.as_view(), name='auction-bid'),

    # Current user
    path('users/me/watchlist/', views.WatchlistView.as_view(), name='watchlist'),
    path('users/me/watchlist/<int:pk>/', views.WatchlistDeleteView.as_view(), name='watchlist-delete'),
    path('users/me/won/', views.WonAuctionsView.as_view(), name='won-auctions'),
    path('users/me/auctions/', views.MyAuctionsView.as_view(), name='my-auctions'),

    # Categories
    path('categories/', views.CategoryListView.as_view(), name='categories'),
]
