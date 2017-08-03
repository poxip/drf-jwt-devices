from datetime import datetime

from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import ugettext as _
from rest_framework import serializers
from rest_framework_jwt.compat import Serializer
from rest_framework_jwt.serializers import JSONWebTokenSerializer as OriginalJSONWebTokenSerializer
from rest_framework_jwt.settings import api_settings as rfj_settings

from jwt_devices.models import Device
from jwt_devices.settings import api_settings

User = get_user_model()

jwt_payload_handler = rfj_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = rfj_settings.JWT_ENCODE_HANDLER
jwt_devices_payload_handler = api_settings.JWT_DEVICES_PAYLOAD_HANDLER
jwt_devices_encode_handler = api_settings.JWT_DEVICES_ENCODE_HANDLER


class JSONWebTokenSerializer(OriginalJSONWebTokenSerializer):
    """
    Serializer used to obtain permanent token.
    """
    def validate(self, attrs):
        credentials = {
            self.username_field: attrs.get(self.username_field),
            "password": attrs.get("password")
        }

        if all(credentials.values()):
            user = authenticate(**credentials)

            if user:
                if not user.is_active:
                    msg = _("User account is disabled.")
                    raise serializers.ValidationError(msg)

                data = {
                    "user": user
                }
                if api_settings.JWT_PERMANENT_TOKEN_AUTH:
                    headers = self.context["request"].META
                    device_name = headers.get("HTTP_X_DEVICE_MODEL")
                    user_agent = headers.get("HTTP_USER_AGENT", "")
                    if not device_name:
                        device_name = user_agent
                        device_details = ""
                    else:
                        device_details = user_agent

                    device = Device.objects.create(
                        user=user, last_request_datetime=datetime.now(),
                        name=device_name, details=device_details)

                    data["token"] = jwt_devices_encode_handler(jwt_devices_payload_handler(user, device=device))
                    data["device"] = device
                else:
                    data["token"] = jwt_encode_handler(jwt_payload_handler(user))

                return data
            else:
                msg = _("Unable to log in with provided credentials.")
                raise serializers.ValidationError(msg)
        else:
            msg = _("Must include \"{username_field}\" and \"password\".")
            msg = msg.format(username_field=self.username_field)
            raise serializers.ValidationError(msg)


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ["id", "created", "name", "details", "last_request_datetime"]


class DeviceTokenRefreshSerializer(Serializer):
    permanent_token = serializers.CharField(required=True)

    def validate(self, attrs):
        permanent_token = attrs["permanent_token"]
        try:
            device = Device.objects.get(permanent_token=permanent_token)
        except Device.DoesNotExist:
            raise serializers.ValidationError({"permanent_token": _("Invalid permanent_token value.")})

        now = datetime.now()
        if now > device.last_request_datetime + api_settings.JWT_PERMANENT_TOKEN_EXPIRATION_DELTA:
            device.delete()
            raise serializers.ValidationError({"permanent_token": _("Permanent token has expired.")})

        if now > device.last_request_datetime + api_settings.JWT_PERMANENT_TOKEN_EXPIRATION_ACCURACY:
            device.last_request_datetime = now
            device.save()

        payload = jwt_devices_payload_handler(device.user, device=device)
        return {
            "token": jwt_devices_encode_handler(payload),
            "user": device.user
        }