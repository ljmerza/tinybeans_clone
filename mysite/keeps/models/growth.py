"""A child's growth log: height and weight measured on a date."""

import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

# Stored metric, at the precision a home tape or scale gives: 1 mm and 1 g.
# That is finer than the imperial display (0.1 in, 0.1 oz), so a value typed
# in imperial reads back the same.
HEIGHT_MIN_CM = Decimal("1.0")
HEIGHT_MAX_CM = Decimal("250.0")
WEIGHT_MIN_KG = Decimal("0.100")
WEIGHT_MAX_KG = Decimal("250.000")
GROWTH_NOTE_MAX_LENGTH = 200


class GrowthMeasurement(models.Model):
    """One height and/or weight reading for a child, on a date.

    Owned by the child's person in one circle, the same record the person page
    shows, so who can see and change it follows that circle: every member can
    see it, only its admins can add, change or delete it.

    Attributes:
        person: The child's person; always a child-kind person
        measured_on: The day it was measured
        height_cm: Height in centimetres, to 0.1 cm (optional)
        weight_kg: Weight in kilograms, to the gram (optional)
        note: Optional short note, e.g. "4 month checkup"
        created_by: Who logged it (null once that user is deleted)
        created_at: When it was logged
        updated_at: When it was last changed
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person = models.ForeignKey("keeps.Person", on_delete=models.CASCADE, related_name="growth_measurements")
    measured_on = models.DateField()
    height_cm = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(HEIGHT_MIN_CM), MaxValueValidator(HEIGHT_MAX_CM)],
    )
    weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(WEIGHT_MIN_KG), MaxValueValidator(WEIGHT_MAX_KG)],
    )
    note = models.CharField(max_length=GROWTH_NOTE_MAX_LENGTH, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="growth_measurements_created",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["measured_on", "created_at", "id"]
        indexes = [
            models.Index(fields=["person", "measured_on"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(height_cm__isnull=False) | models.Q(weight_kg__isnull=False),
                name="keeps_growth_height_or_weight",
            ),
            models.CheckConstraint(
                condition=models.Q(height_cm__isnull=True) | models.Q(height_cm__gt=0),
                name="keeps_growth_height_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(weight_kg__isnull=True) | models.Q(weight_kg__gt=0),
                name="keeps_growth_weight_positive",
            ),
        ]

    def __str__(self):
        return f"{self.person.name} on {self.measured_on}"

    def clean(self):
        super().clean()
        errors = {}
        if self.height_cm is None and self.weight_kg is None:
            errors["height_cm"] = "Enter a height, a weight or both."
        if self.person_id and not self.person.child_id:
            errors["person"] = "Growth can only be logged for a child."
        if self.measured_on:
            # A day of slack, so someone ahead of UTC can log "today".
            if self.measured_on > timezone.localdate() + timedelta(days=1):
                errors["measured_on"] = "The date can't be in the future."
            elif self.person_id and self.person.child_id:
                birthdate = self.person.child.birthdate
                if birthdate and self.measured_on < birthdate:
                    errors["measured_on"] = "The date can't be before the child's birthdate."
        if errors:
            raise ValidationError(errors)
