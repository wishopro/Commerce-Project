from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),

    # Auth (from distribution)
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),

    # Listings
    path("new/", views.new_listing, name="new_listing"),
    path("listing/<int:listing_id>/", views.listing_detail, name="listing_detail"),
    path("listing/<int:listing_id>/close/", views.close_listing, name="close_listing"),

    # Watchlist
    path("listing/<int:listing_id>/watchlist/", views.toggle_watchlist, name="toggle_watchlist"),
    path("watchlist/", views.watchlist, name="watchlist"),

    # Categories
    path("categories/", views.categories, name="categories"),
    path("categories/<int:category_id>/", views.category_detail, name="category_detail"),
]
