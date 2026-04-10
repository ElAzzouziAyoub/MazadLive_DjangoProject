from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from .models import Auction, Bid, Category, Watchlist


def home(request):
    qs = Auction.objects.select_related('seller', 'category').annotate(bid_count=Count('bids'))

    status_filter = request.GET.get('status', 'LIVE').upper()
    category_slug = request.GET.get('category', '')
    query = request.GET.get('q', '')

    if status_filter:
        qs = qs.filter(status=status_filter)
    if category_slug:
        qs = qs.filter(category__slug=category_slug)
    if query:
        qs = qs.filter(Q(title__icontains=query) | Q(description__icontains=query))

    from django.core.paginator import Paginator
    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'auctions/home.html', {
        'auctions': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'categories': Category.objects.all(),
    })


def auction_detail(request, pk):
    auction = get_object_or_404(
        Auction.objects.select_related('seller', 'category', 'winner'),
        pk=pk,
    )
    bids = auction.bids.select_related('bidder').order_by('-timestamp')

    in_watchlist = False
    watchlist_id = None
    if request.user.is_authenticated:
        entry = Watchlist.objects.filter(user=request.user, auction=auction).first()
        if entry:
            in_watchlist = True
            watchlist_id = entry.pk

    return render(request, 'auctions/auction_detail.html', {
        'auction': auction,
        'bids': bids,
        'in_watchlist': in_watchlist,
        'watchlist_id': watchlist_id,
    })


@login_required
@require_POST
def place_bid(request, pk):
    auction = get_object_or_404(Auction, pk=pk)

    if auction.status != Auction.STATUS_LIVE:
        messages.error(request, 'This auction is not currently live.')
        return redirect('auction_detail', pk=pk)

    if auction.seller == request.user:
        messages.error(request, 'You cannot bid on your own auction.')
        return redirect('auction_detail', pk=pk)

    try:
        amount = Decimal(request.POST.get('amount', ''))
    except InvalidOperation:
        messages.error(request, 'Invalid bid amount.')
        return redirect('auction_detail', pk=pk)

    if amount <= auction.current_price:
        messages.error(request, f'Bid must be higher than the current price ({auction.current_price} MAD).')
        return redirect('auction_detail', pk=pk)

    auto_bid_max_raw = request.POST.get('auto_bid_max', '').strip()
    is_auto = False
    if auto_bid_max_raw:
        try:
            Decimal(auto_bid_max_raw)
            is_auto = True
        except InvalidOperation:
            pass

    Bid.objects.create(auction=auction, bidder=request.user, amount=amount, is_auto_bid=is_auto)
    auction.current_price = amount
    auction.save(update_fields=['current_price', 'updated_at'])

    messages.success(request, f'Bid of {amount} MAD placed successfully!')
    return redirect('auction_detail', pk=pk)


@login_required
def create_auction(request):
    categories = Category.objects.all()
    errors = []
    form_data = {}

    if request.method == 'POST':
        form_data = request.POST.dict()
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category')
        starting_price_raw = request.POST.get('starting_price', '')
        reserve_price_raw = request.POST.get('reserve_price', '').strip()
        start_time_raw = request.POST.get('start_time', '')
        end_time_raw = request.POST.get('end_time', '')

        if not title:
            errors.append('Title is required.')
        if not category_id:
            errors.append('Category is required.')

        starting_price = None
        try:
            starting_price = Decimal(starting_price_raw)
            if starting_price <= 0:
                errors.append('Starting price must be positive.')
        except InvalidOperation:
            errors.append('Invalid starting price.')

        reserve_price = None
        if reserve_price_raw:
            try:
                reserve_price = Decimal(reserve_price_raw)
            except InvalidOperation:
                errors.append('Invalid reserve price.')

        start_time = parse_datetime(start_time_raw) if start_time_raw else None
        end_time = parse_datetime(end_time_raw) if end_time_raw else None

        if not start_time:
            errors.append('Start time is required.')
        if not end_time:
            errors.append('End time is required.')
        if start_time and end_time and end_time <= start_time:
            errors.append('End time must be after start time.')

        if not errors:
            category = get_object_or_404(Category, pk=category_id)
            now = timezone.now()
            status = Auction.STATUS_LIVE if start_time <= now else Auction.STATUS_SCHEDULED
            Auction.objects.create(
                seller=request.user,
                title=title,
                description=description,
                category=category,
                starting_price=starting_price,
                reserve_price=reserve_price,
                current_price=starting_price,
                start_time=start_time,
                end_time=end_time,
                status=status,
            )
            messages.success(request, 'Auction created successfully!')
            return redirect('my_auctions')

    return render(request, 'auctions/create_auction.html', {
        'categories': categories,
        'errors': errors,
        'form_data': form_data,
    })


@login_required
def watchlist_view(request):
    items = Watchlist.objects.filter(user=request.user).select_related('auction__category', 'auction__seller')
    return render(request, 'auctions/watchlist.html', {'items': items})


@login_required
@require_POST
def watchlist_add(request):
    auction_id = request.POST.get('auction_id')
    auction = get_object_or_404(Auction, pk=auction_id)
    Watchlist.objects.get_or_create(user=request.user, auction=auction)
    messages.success(request, 'Added to your watchlist.')
    return redirect('auction_detail', pk=auction.pk)


@login_required
@require_POST
def watchlist_remove(request, pk):
    entry = get_object_or_404(Watchlist, pk=pk, user=request.user)
    auction_pk = entry.auction_id
    entry.delete()
    messages.success(request, 'Removed from watchlist.')
    next_url = request.POST.get('next', '')
    if next_url == 'watchlist':
        return redirect('watchlist')
    return redirect('auction_detail', pk=auction_pk)


@login_required
def my_auctions(request):
    auctions = Auction.objects.filter(seller=request.user).select_related('category').annotate(bid_count=Count('bids'))
    return render(request, 'auctions/my_auctions.html', {'auctions': auctions})


@login_required
def won_auctions(request):
    auctions = Auction.objects.filter(winner=request.user).select_related('category')
    return render(request, 'auctions/won.html', {'auctions': auctions})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get('next', '/'))
        return render(request, 'auctions/login.html', {'form': {'errors': True}})
    return render(request, 'auctions/login.html', {})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    form_errors = {}
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if User.objects.filter(username=username).exists():
            form_errors['username'] = ['Username already taken.']
        if password1 != password2:
            form_errors['password2'] = ['Passwords do not match.']
        if len(password1) < 8:
            form_errors['password1'] = ['Password must be at least 8 characters.']

        if not form_errors:
            user = User.objects.create_user(username=username, email=email, password=password1)
            login(request, user)
            messages.success(request, f'Welcome, {username}!')
            return redirect('home')

    return render(request, 'auctions/register.html', {'form': type('F', (), {'errors': form_errors})()})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('home')
