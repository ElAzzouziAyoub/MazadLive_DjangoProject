from django.contrib import admin

from .models import Auction, Bid, Category, Watchlist


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ['name', 'slug']
    list_display = ['name', 'slug']


@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    search_fields = ['title', 'seller__username']
    list_display = [
        'id',
        'title',
        'seller',
        'category',
        'status',
        'starting_price',
        'current_price',
        'start_time',
        'end_time',
        'winner',
    ]
    list_filter = ['status', 'category', 'end_time']
    autocomplete_fields = ['seller', 'winner', 'category']


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    search_fields = ['auction__title', 'bidder__username']
    list_display = ['id', 'auction', 'bidder', 'amount', 'timestamp', 'is_auto_bid']
    list_filter = ['is_auto_bid']
    autocomplete_fields = ['auction', 'bidder']


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    search_fields = ['user__username', 'auction__title']
    list_display = ['id', 'user', 'auction', 'created_at']
    autocomplete_fields = ['user', 'auction']
