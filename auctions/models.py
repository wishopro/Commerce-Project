from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    # Reverse M2M: user.watchlist -> Listings user is watching
    pass


class Category(models.Model):
    name = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.name


class Listing(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    starting_price = models.DecimalField(max_digits=10, decimal_places=2)
    bid_increase = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="listings")
    active = models.BooleanField(default=True)  # manual close
    end_time = models.DateTimeField(null=True, blank=True)  # auto-close by time

    image_url = models.URLField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="listings")

    # watchers: user.watchlist (reverse name)
    watchers = models.ManyToManyField(User, related_name="watchlist", blank=True)

    def __str__(self):
        return self.name

    @property
    def highest_bid(self):
        return self.bids.order_by("-amount", "-created_at").first()

    @property
    def current_price(self):
        return self.highest_bid.amount if self.highest_bid else self.starting_price

    # Listing model
    @property
    def is_active(self):
        # Ignore end_time completely; manual close only
        return self.active


    @property
    def winner(self):
        if self.is_active:
            return None
        top = self.highest_bid
        return top.user if top else None


class Bid(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="bids")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bids")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} bid ${self.amount} on {self.listing.name}"


class Comment(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.listing.name}"
