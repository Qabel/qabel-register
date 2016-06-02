import codecs

from rest_framework import serializers
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from register_service.logic import UpdateRequest, UpdateItem
from register_service.models import Identity, Entry
from register_service.crypto import decode_public_key


class IdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Identity
        fields = ('alias', 'public_key', 'drop_url')

    def update(self, instance, validated_data):
        instance.alias = validated_data.get('alias', instance.alias)
        instance.public_key = validated_data.get('public_key', instance.public_key)
        instance.drop_url = validated_data.get('drop_url', instance.drop_url)
        instance.save()
        return instance

    def validate_public_key(self, value):
        try:
            decode_public_key(value)
        except ValueError:
            raise ValidationError('public key must be 64 hex characters.') from None
        return value


class UpdateItemSerializer(serializers.Serializer):
    action = serializers.ChoiceField(('create', 'delete'))
    field = serializers.ChoiceField(Entry.FIELDS)
    value = serializers.CharField()

    def create(self, validated_data):
        return UpdateItem(action=validated_data['action'],
                          field=validated_data['field'],
                          value=validated_data['value'])


class UpdateRequestSerializer(serializers.Serializer):
    items = UpdateItemSerializer(many=True, required=True)
    identity = IdentitySerializer(required=True)

    def create(self, validated_data):
        items = []
        for item in validated_data['items']:
            # XXX easier way?
            subser = UpdateItemSerializer(data=item)
            subser.is_valid(True)
            items.append(subser.save())
        idser = IdentitySerializer(data=validated_data['identity'])
        idser.is_valid(True)
        identity = idser.save()
        request = UpdateRequest(identity, items)
        request.json_request = UpdateRequestSerializer(request).data
        return request

    def validate_items(self, value):
        if not value:
            raise ValidationError('At least one update item is required.')
        items = []
        for item in value:
            if item in items:
                raise ValidationError('Duplicate update items are not allowed.')
            items.append(item)
        return value
