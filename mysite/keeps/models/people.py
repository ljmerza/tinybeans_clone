"""People who can be tagged on a circle's posts."""

import uuid

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

# Matches ChildProfile.display_name and PetProfile.name.
PERSON_NAME_MAX_LENGTH = 150


class PersonKind(models.TextChoices):
    """What a person stands for; derived from which link is set."""

    CHILD = "child", "Child"
    MEMBER = "member", "Member"
    PET = "pet", "Pet"
    OTHER = "other", "Other"


class Person(models.Model):
    """Someone (or some pet) who can be tagged on one circle's posts.

    A person is a child profile, a circle member, a pet, or just a name such
    as "Grandma Jo" (none of the links set). Each child, member and pet has at
    most one person per circle. The name is copied from the linked profile
    when the person is created and is not kept in step with it afterwards.

    Attributes:
        circle: The circle whose posts the person can be tagged on
        name: Shown on posts and as the person page's title
        child: The child profile this person is, if any
        user: The circle member this person is, if any
        pet: The pet this person is, if any
        created_by: Who added a free-text person (null for linked ones)
        created_at: When it was created
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circle = models.ForeignKey("users.Circle", on_delete=models.CASCADE, related_name="people")
    name = models.CharField(max_length=PERSON_NAME_MAX_LENGTH)
    child = models.ForeignKey(
        "users.ChildProfile", null=True, blank=True, on_delete=models.CASCADE, related_name="people"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="people"
    )
    pet = models.ForeignKey("users.PetProfile", null=True, blank=True, on_delete=models.CASCADE, related_name="people")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="people_created",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = [Lower("name"), "id"]
        verbose_name_plural = "people"
        constraints = [
            models.UniqueConstraint(
                fields=["circle", "child"], condition=models.Q(child__isnull=False), name="keeps_person_unique_child"
            ),
            models.UniqueConstraint(
                fields=["circle", "user"], condition=models.Q(user__isnull=False), name="keeps_person_unique_user"
            ),
            models.UniqueConstraint(
                fields=["circle", "pet"], condition=models.Q(pet__isnull=False), name="keeps_person_unique_pet"
            ),
            # Free-text names are matched case-insensitively within a circle.
            models.UniqueConstraint(
                "circle",
                Lower("name"),
                condition=models.Q(child__isnull=True, user__isnull=True, pet__isnull=True),
                name="keeps_person_unique_free_text_name",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.circle})"

    @property
    def kind(self) -> str:
        if self.child_id:
            return PersonKind.CHILD
        if self.user_id:
            return PersonKind.MEMBER
        if self.pet_id:
            return PersonKind.PET
        return PersonKind.OTHER


class KeepPerson(models.Model):
    """One person tagged on one keep.

    Attributes:
        keep: The post
        person: Who is in it; always from the keep's circle
        media: Reserved for tagging one photo of a post; unused for now
        added_by: Who tagged them (null for imported tags or a deleted user)
        added_at: When they were tagged
    """

    keep = models.ForeignKey("keeps.Keep", on_delete=models.CASCADE, related_name="person_tags")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="keep_tags")
    media = models.ForeignKey(
        "keeps.KeepMedia", null=True, blank=True, on_delete=models.CASCADE, related_name="person_tags"
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="person_tags_added",
    )
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["keep", "person"], name="keeps_unique_keep_person"),
        ]

    def __str__(self):
        return f"{self.person} on {self.keep_id}"
