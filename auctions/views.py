from decimal import Decimal, InvalidOperation
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Bid, Comment, Listing, User, Category


def index(request):
    # show only active listings (spec)
    all_listings = Listing.objects.order_by("-created_at")
    listings = [l for l in all_listings if l.is_active]
    return render(request, "auctions/index.html", {"listings": listings})


# ------- Auth (from distribution, with small robustness tweaks) -------

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("index")
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return redirect("index")


def register(request):
    if request.method == "POST":
        username = request.POST.get("username", "")
        email = request.POST.get("email", "")

        password = request.POST.get("password", "")
        confirmation = request.POST.get("confirmation", "")
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except Exception:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return redirect("index")
    else:
        return render(request, "auctions/register.html")


# ---------------- Listings ----------------

@login_required
def new_listing(request):
    if request.method == "POST":
        name = (request.POST.get("Listing_name") or "").strip()
        description = (request.POST.get("Listing_description") or "").strip()
        image_url = (request.POST.get("Image_url") or "").strip() or None
        category_name = (request.POST.get("Category_name") or "").strip() or None

        try:
            starting_price = Decimal(request.POST.get("Starting_price", "0"))
        except (InvalidOperation, TypeError):
            starting_price = Decimal("0")

        try:
            bid_increase = Decimal(request.POST.get("Bid_increase", "1"))
        except (InvalidOperation, TypeError):
            bid_increase = Decimal("1")

        # ---- FIXED: robust end_time parsing and future check ----
        end_time = None
        end_time_raw = request.POST.get("End_time")

        if end_time_raw:
            def _parse_dt(s: str) -> datetime:
                # Handle both with and without seconds from <input type="datetime-local">
                for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
                    try:
                        return datetime.strptime(s, fmt)
                    except ValueError:
                        continue
                raise ValueError("Invalid end time format")

            try:
                naive_local = _parse_dt(end_time_raw)                     # naive
                tz = timezone.get_current_timezone()                      # from settings.TIME_ZONE
                end_time = timezone.make_aware(naive_local, tz)           # aware in your TZ
                if end_time <= timezone.now():
                    messages.error(request, "End time must be in the future.")
                    return render(request, "auctions/new_listing.html")
            except ValueError:
                messages.error(request, "Invalid end time format.")
                return render(request, "auctions/new_listing.html")
        # ---------------------------------------------------------

        category = None
        if category_name:
            category, _ = Category.objects.get_or_create(name=category_name)

        listing = Listing.objects.create(
            name=name,
            description=description,
            starting_price=starting_price,
            bid_increase=bid_increase,
            owner=request.user,
            end_time=end_time,
            image_url=image_url,
            category=category,
        )
        messages.success(request, "Listing created.")
        return redirect("listing_detail", listing_id=listing.id)

    # GET
    return render(request, "auctions/new_listing.html")


def listing_detail(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)
    bids = listing.bids.order_by("-created_at")
    comments = listing.comments.order_by("-created_at")

    if request.method == "POST":
        # place a custom amount bid
        if "place_bid" in request.POST and request.user.is_authenticated and listing.is_active:
            try:
                amount = Decimal(request.POST.get("bid_amount", "0"))
            except (InvalidOperation, TypeError):
                amount = Decimal("0")

            top = listing.highest_bid
            # First bid must be >= starting price. Next bids must be > current price.
            min_required = listing.starting_price if top is None else listing.current_price
            ok = (amount >= min_required) if top is None else (amount > min_required)

            if ok:
                Bid.objects.create(listing=listing, user=request.user, amount=amount)
                messages.success(request, f"Bid placed at ${amount}.")
            else:
                if top is None:
                    messages.error(request, f"Your bid must be at least the starting price (${min_required}).")
                else:
                    messages.error(request, f"Your bid must be greater than the current price (${min_required}).")
            return redirect("listing_detail", listing_id=listing.id)

        # quick increment bid
        if "increment_bid" in request.POST and request.user.is_authenticated and listing.is_active:
            next_amount = (listing.current_price or Decimal("0")) + (listing.bid_increase or Decimal("1"))
            # next_amount must also respect first-bid rule if no bids exist
            top = listing.highest_bid
            min_required = listing.starting_price if top is None else listing.current_price
            if (top is None and next_amount >= min_required) or (top is not None and next_amount > min_required):
                Bid.objects.create(listing=listing, user=request.user, amount=next_amount)
                messages.success(request, f"Quick bid placed at ${next_amount}.")
            else:
                messages.error(request, "Quick bid did not meet minimum required amount.")
            return redirect("listing_detail", listing_id=listing.id)

        # comment
        if "comment_content" in request.POST and request.user.is_authenticated:
            content = (request.POST.get("comment_content") or "").strip()
            if content:
                Comment.objects.create(listing=listing, user=request.user, content=content)
                messages.success(request, "Comment posted.")
            else:
                messages.error(request, "Comment cannot be empty.")
            return redirect("listing_detail", listing_id=listing.id)

        # delete (optional)
        if "delete_listing" in request.POST and request.user == listing.owner:
            listing.delete()
            messages.info(request, "Listing deleted.")
            return redirect("index")

    # ---- Added 'now' to help debug time comparisons in the template ----
    return render(request, "auctions/listing_detail.html", {
        "listing": listing,
        "bids": bids,
        "comments": comments,
        "now": timezone.now(),
    })


@login_required
def close_listing(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id, owner=request.user)
    if request.method == "POST":
        listing.active = False
        listing.save()
        messages.info(request, "Auction closed.")
    return redirect("listing_detail", listing_id=listing.id)


@login_required
def toggle_watchlist(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)
    if request.user in listing.watchers.all():
        listing.watchers.remove(request.user)
        messages.info(request, "Removed from watchlist.")
    else:
        listing.watchers.add(request.user)
        messages.success(request, "Added to watchlist.")
    return redirect("listing_detail", listing_id=listing.id)


@login_required
def watchlist(request):
    listings = request.user.watchlist.all().order_by("-created_at")
    return render(request, "auctions/watchlist.html", {"listings": listings})


# ---------------- Categories ----------------

def categories(request):
    cats = Category.objects.order_by("name")
    return render(request, "auctions/categories.html", {"categories": cats})


def category_detail(request, category_id):
    cat = get_object_or_404(Category, id=category_id)
    listings = [l for l in cat.listings.all() if l.is_active]
    return render(request, "auctions/category_detail.html", {
        "category": cat,
        "listings": listings
    })
