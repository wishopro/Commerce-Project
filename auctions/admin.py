from django.contrib import admin
from .models import Listing, Bid, Comment, Category

@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "active", "end_time", "created_at", "category")
    list_filter = ("active", "category")
    search_fields = ("name", "description", "owner__username")

@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "user", "amount", "created_at")
    list_filter = ("created_at",)
    search_fields = ("listing__name", "user__username")

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("listing__name", "user__username", "content")

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
