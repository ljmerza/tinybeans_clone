"""Request shapes for the in-app AI settings API. There is deliberately no field for a URL, key or model."""

from rest_framework import serializers


class AiSettingsUpdateSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    # Must be true to turn AI on: the admin accepts that captions go to the operator's AI service.
    acknowledge_data_sharing = serializers.BooleanField(default=False)

    def validate(self, attrs):
        # Refuse rather than ignore anything else, e.g. a base_url or model.
        unknown = sorted(set(self.initial_data) - set(self.fields))
        if unknown:
            raise serializers.ValidationError({field: "Not an accepted field." for field in unknown})
        return attrs
