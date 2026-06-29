from django.db import models

class PostMetadataQuerySet(models.QuerySet):
    def for_category(self, category):
        return self.filter(category=category)

    def popular(self, threshold=20.0):
        return self.filter(engagement_score__gte=threshold)

    def trending(self, threshold=20.0):
        return self.filter(trending_score__gte=threshold)

class PostMetadataManager(models.Manager):
    def get_queryset(self):
        return PostMetadataQuerySet(self.model, using=self._db)

    def for_category(self, category):
        return self.get_queryset().for_category(category)

    def popular(self, threshold=20.0):
        return self.get_queryset().popular(threshold)

    def trending(self, threshold=20.0):
        return self.get_queryset().trending(threshold)


class ReelMetadataQuerySet(models.QuerySet):
    def for_category(self, category):
        return self.filter(category=category)

    def popular(self, threshold=20.0):
        return self.filter(engagement_score__gte=threshold)

class ReelMetadataManager(models.Manager):
    def get_queryset(self):
        return ReelMetadataQuerySet(self.model, using=self._db)

    def for_category(self, category):
        return self.get_queryset().for_category(category)

    def popular(self, threshold=20.0):
        return self.get_queryset().popular(threshold)
