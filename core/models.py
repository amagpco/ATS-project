import uuid

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base model that adds `created_at` and `updated_at` audit fields.

    Use this mixin for any entity that should track when it was created or
    last updated. The fields are indexed because most dashboard reports and
    API endpoints will sort or filter by creation time.
    """

    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """
    Abstract base model that uses UUIDs as primary keys.

    UUID primary keys make it safer to expose identifiers publicly (e.g. in
    API responses) and help with sharding in distributed systems.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True
