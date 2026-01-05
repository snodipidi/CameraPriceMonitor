from django.contrib import admin
from .models import Brand, CameraModel, Listing, PriceSnapshot, WatchItem

admin.site.register(Brand)
admin.site.register(CameraModel)
admin.site.register(Listing)
admin.site.register(PriceSnapshot)
admin.site.register(WatchItem)
