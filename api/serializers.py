from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from .models import Member


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=200)
    timestamp = serializers.DateTimeField(read_only=True)


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = [
            "id",
            "username",
            "email",
            "avatar_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MemberRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6, allow_blank=False)

    class Meta:
        model = Member
        fields = ["username", "email", "password", "avatar_url"]

    def validate_username(self, value: str) -> str:
        if Member.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def validate_email(self, value: str) -> str:
        # Case-insensitive uniqueness for emails
        if Member.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already in use.")
        return value

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data["password"])  # hash password
        return super().create(validated_data)


class MemberUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ["username", "email", "avatar_url"]
        extra_kwargs = {
            "username": {"required": False},
            "email": {"required": False},
            "avatar_url": {"required": False},
        }

    def validate(self, attrs):
        instance: Member = self.instance
        username = attrs.get("username")
        email = attrs.get("email")

        if username is not None:
            qs = Member.objects.filter(username=username)
            if instance is not None:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"username": "Username already taken."})

        if email is not None:
            qs = Member.objects.filter(email__iexact=email)
            if instance is not None:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"email": "Email already in use."})

        return attrs
