"""Tagging people on posts: the circle's taggable people, and setting a post's tags.

A post's people and its ``children`` (the Tinybeans importer's child links)
are kept in step both ways: tagging a child's person here also links the
child, and linking a child (e.g. by the importer) tags its person through the
``m2m_changed`` mirror in ``signals``. The mirror never writes ``children``,
so the two can't loop.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from mysite.circles.models import CircleMembership

from .models import PERSON_NAME_MAX_LENGTH, KeepPerson, Person


def clip_name(name) -> str:
    return (name or "").strip()[:PERSON_NAME_MAX_LENGTH]


def ensure_circle_people(circle) -> None:
    """Create the missing person for each of the circle's child profiles, members and pets.

    Done when the circle's people are listed, so every one of them can be
    picked by id. Existing people keep their names.
    """
    existing = Person.objects.filter(circle=circle).values_list("child_id", "user_id", "pet_id")
    children, users, pets = set(), set(), set()
    for child_id, user_id, pet_id in existing:
        children.add(child_id)
        users.add(user_id)
        pets.add(pet_id)

    missing = [
        Person(circle=circle, child=child, name=clip_name(child.display_name))
        for child in circle.children.all()
        if child.id not in children
    ]
    missing += [
        Person(circle=circle, user=membership.user, name=clip_name(membership.user.display_name))
        for membership in CircleMembership.objects.filter(circle=circle).select_related("user")
        if membership.user_id not in users
    ]
    missing += [
        Person(circle=circle, pet=pet, name=clip_name(pet.name)) for pet in circle.pets.all() if pet.id not in pets
    ]
    if missing:
        # A concurrent request may have created some of them already.
        Person.objects.bulk_create(missing, ignore_conflicts=True)


def person_for_child(circle_id, child) -> Person:
    """The circle's person for a child profile, created if needed."""
    person, _ = Person.objects.get_or_create(
        circle_id=circle_id, child=child, defaults={"name": clip_name(child.display_name)}
    )
    return person


def resolve_circle_people(circle_id, person_ids) -> list[Person]:
    """The people with these ids; every one must belong to the circle."""
    wanted = set(person_ids)
    people = list(Person.objects.filter(circle_id=circle_id, id__in=wanted))
    if len(people) != len(wanted):
        raise ValidationError({"people": "Only people from the post's circle can be tagged."})
    return people


@transaction.atomic
def set_keep_people(keep, people, added_by) -> None:
    """Make ``people`` the post's tags, replacing the old ones, and match its child links."""
    wanted = {person.id: person for person in people}
    current = set(KeepPerson.objects.filter(keep=keep).values_list("person_id", flat=True))
    removed = current - wanted.keys()
    if removed:
        KeepPerson.objects.filter(keep=keep, person_id__in=removed).delete()
    added = [
        KeepPerson(keep=keep, person=person, added_by=added_by) for pid, person in wanted.items() if pid not in current
    ]
    if added:
        KeepPerson.objects.bulk_create(added, ignore_conflicts=True)
    # The mirror finds these tags already in place, so it only adds or drops
    # the child links.
    keep.children.set([person.child_id for person in people if person.child_id])
