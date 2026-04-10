from django.utils import timezone
from rest_framework import serializers

from .models import Auction, Bid, Category, Watchlist


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class BidSerializer(serializers.ModelSerializer):
    bidder_username = serializers.CharField(source='bidder.username', read_only=True)

    class Meta:
        model = Bid
        fields = ['id', 'bidder_username', 'amount', 'timestamp', 'is_auto_bid']
        read_only_fields = ['id', 'bidder_username', 'timestamp', 'is_auto_bid']


class AuctionListSerializer(serializers.ModelSerializer):
    seller_username = serializers.CharField(source='seller.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    bid_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Auction
        fields = [
            'id', 'title', 'seller_username', 'category', 'category_name',
            'starting_price', 'current_price', 'status',
            'start_time', 'end_time', 'bid_count',
        ]


class AuctionDetailSerializer(serializers.ModelSerializer):
    seller_username = serializers.CharField(source='seller.username', read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    bids = BidSerializer(many=True, read_only=True)
    winner_username = serializers.CharField(source='winner.username', read_only=True, allow_null=True)

    class Meta:
        model = Auction
        fields = [
            'id', 'title', 'description', 'seller_username',
            'category', 'category_id',
            'starting_price', 'reserve_price', 'current_price',
            'start_time', 'end_time', 'status',
            'winner_username', 'bids',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'seller_username', 'current_price', 'status', 'winner_username', 'created_at', 'updated_at']

    def validate(self, data):
        start = data.get('start_time')
        end = data.get('end_time')
        if start and end and end <= start:
            raise serializers.ValidationError({'end_time': 'End time must be after start time.'})
        return data

    def create(self, validated_data):
        validated_data['seller'] = self.context['request'].user
        return super().create(validated_data)


class PlaceBidSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    auto_bid_max = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)

    def validate(self, data):
        auction = self.context['auction']
        user = self.context['request'].user
        amount = data['amount']

        if auction.status != Auction.STATUS_LIVE:
            raise serializers.ValidationError('This auction is not currently live.')
        if auction.seller == user:
            raise serializers.ValidationError('You cannot bid on your own auction.')
        if amount <= auction.current_price:
            raise serializers.ValidationError(
                f'Bid must be higher than the current price ({auction.current_price}).'
            )
        return data


class WatchlistSerializer(serializers.ModelSerializer):
    auction = AuctionListSerializer(read_only=True)
    auction_id = serializers.PrimaryKeyRelatedField(
        queryset=Auction.objects.all(), source='auction', write_only=True
    )

    class Meta:
        model = Watchlist
        fields = ['id', 'auction', 'auction_id', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_auction_id(self, auction):
        user = self.context['request'].user
        if Watchlist.objects.filter(user=user, auction=auction).exists():
            raise serializers.ValidationError('Already in your watchlist.')
        return auction

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
