"""Serializers for a child's growth log."""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from ..models import GrowthMeasurement


class GrowthMeasurementSerializer(serializers.ModelSerializer):
    """One measurement. Heights and weights are numbers in cm and kg, never strings."""

    height_cm = serializers.DecimalField(
        max_digits=4, decimal_places=1, allow_null=True, required=False, coerce_to_string=False
    )
    weight_kg = serializers.DecimalField(
        max_digits=6, decimal_places=3, allow_null=True, required=False, coerce_to_string=False
    )

    class Meta:
        model = GrowthMeasurement
        fields = ["id", "measured_on", "height_cm", "weight_kg", "note", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def to_internal_value(self, data):
        # Round to the stored precision instead of rejecting extra digits, so a
        # value converted from imperial (e.g. 20.25 in = 51.435 cm) is accepted.
        if hasattr(data, "copy"):
            data = data.copy()
        for name, places in (("height_cm", 1), ("weight_kg", 3)):
            value = data.get(name) if hasattr(data, "get") else None
            if isinstance(value, int | float) and not isinstance(value, bool):
                data[name] = round(value, places)
        return super().to_internal_value(data)

    def validate(self, attrs):
        # Run the model's checks (one of height/weight, a child, sensible date)
        # on the measurement as it would be saved.
        instance = self.instance or GrowthMeasurement(person=self.context["person"])
        for name, value in attrs.items():
            setattr(instance, name, value)
        try:
            instance.full_clean(exclude=["created_by"])
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from None
        return attrs
