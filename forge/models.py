import uuid

from django.db import models


class TimestampModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """An entire abstract model is almost overkill for this, but it's also
    very easy to forget to use unique=True, or to set the default incorrectly."""

    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

        
class JSONClassField(models.JSONField):
    """
    An instance class needs:
    - __init__ with a single arg (kwargs optional)
    - validate with a single arg for model_instance (optional)
    - should inherit from dict or list
    """

    def __init__(self, instance_class, *args, **kwargs):
        self.instance_class = instance_class

        if issubclass(instance_class, dict):
            kwargs.setdefault("default", dict)
        elif issubclass(instance_class, list):
            kwargs.setdefault("default", list)
        else:
            raise ValueError("instance_class must be a subclass of dict or list")

        kwargs.setdefault("blank", True)

        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["instance_class"] = self.instance_class
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value

        data = super().from_db_value(value, expression, connection)
        return self.instance_class(data)

    def to_python(self, value):
        if value is None:
            return value

        if isinstance(value, self.instance_class):
            return value

        data = super().to_python(value)
        return self.instance_class(data)

    def validate(self, value, model_instance):
        # Do the regular JSON validation
        super().validate(value, model_instance)

        if hasattr(value, "validate"):
            # Call the custom validation method on the instance class
            value.validate(model_instance)
