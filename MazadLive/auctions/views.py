from django.db.models import Count
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Auction, Bid, Category, Watchlist
from .serializers import (
    AuctionDetailSerializer,
    AuctionListSerializer,
    CategorySerializer,
    PlaceBidSerializer,
    WatchlistSerializer,
)


class CategoryListView(generics.ListAPIView):
    """GET /api/categories/ — list all categories"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class AuctionListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/auctions/ — list active (LIVE) auctions
    POST /api/auctions/ — create a new auction listing (auth required)
    """
    def get_queryset(self):
        qs = Auction.objects.annotate(bid_count=Count('bids'))
        status_filter = self.request.query_params.get('status', Auction.STATUS_LIVE)
        category = self.request.query_params.get('category')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')

        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        if category:
            qs = qs.filter(category__slug=category)
        if min_price:
            qs = qs.filter(current_price__gte=min_price)
        if max_price:
            qs = qs.filter(current_price__lte=max_price)
        return qs

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AuctionDetailSerializer
        return AuctionListSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]


class AuctionDetailView(generics.RetrieveAPIView):
    """GET /api/auctions/{id}/ — auction detail with full bid history"""
    serializer_class = AuctionDetailSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Auction.objects.prefetch_related('bids__bidder', 'category')


class PlaceBidView(APIView):
    """POST /api/auctions/{id}/bid/ — place a bid on an auction"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            auction = Auction.objects.get(pk=pk)
        except Auction.DoesNotExist:
            return Response({'detail': 'Auction not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = PlaceBidSerializer(data=request.data, context={'request': request, 'auction': auction})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        amount = serializer.validated_data['amount']
        auto_bid_max = serializer.validated_data.get('auto_bid_max')

        bid = Bid.objects.create(
            auction=auction,
            bidder=request.user,
            amount=amount,
            is_auto_bid=bool(auto_bid_max),
        )

        # Update auction's current price
        auction.current_price = amount
        auction.save(update_fields=['current_price', 'updated_at'])

        return Response(
            {'detail': 'Bid placed successfully.', 'amount': str(bid.amount)},
            status=status.HTTP_201_CREATED,
        )


class WatchlistView(generics.ListCreateAPIView):
    """
    GET  /api/users/me/watchlist/ — list my watchlist
    POST /api/users/me/watchlist/ — add auction to watchlist
    """
    serializer_class = WatchlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Watchlist.objects.filter(user=self.request.user).select_related('auction__category')


class WatchlistDeleteView(generics.DestroyAPIView):
    """DELETE /api/users/me/watchlist/{id}/ — remove from watchlist"""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Watchlist.objects.filter(user=self.request.user)


class WonAuctionsView(generics.ListAPIView):
    """GET /api/users/me/won/ — auctions the current user has won"""
    serializer_class = AuctionListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Auction.objects
            .filter(winner=self.request.user)
            .annotate(bid_count=Count('bids'))
        )


class MyAuctionsView(generics.ListAPIView):
    """GET /api/users/me/auctions/ — auctions the current user is selling"""
    serializer_class = AuctionListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Auction.objects
            .filter(seller=self.request.user)
            .annotate(bid_count=Count('bids'))
        )
