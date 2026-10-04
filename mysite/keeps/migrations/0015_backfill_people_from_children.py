"""Copy every existing keep <-> child profile link into the new people tags.

Each linked child gets one Person in the keep's circle, named after the
profile, and each link becomes a KeepPerson. Children with no linked keeps get
their Person later, when the circle's people are first listed. Idempotent.
The reverse is a no-op: undoing 0014 drops both tables anyway.
"""
from django.db import migrations

NAME_MAX_LENGTH = 150


def backfill_people_from_children(apps, schema_editor):
    Keep = apps.get_model('keeps', 'Keep')
    Person = apps.get_model('keeps', 'Person')
    KeepPerson = apps.get_model('keeps', 'KeepPerson')
    links = Keep.children.through.objects.values_list(
        'keep_id', 'keep__circle_id', 'childprofile_id', 'childprofile__display_name'
    )

    people = {
        (circle_id, child_id): person_id
        for circle_id, child_id, person_id in Person.objects.filter(child__isnull=False).values_list(
            'circle_id', 'child_id', 'id'
        )
    }
    tags = []
    for keep_id, circle_id, child_id, display_name in links.iterator():
        person_id = people.get((circle_id, child_id))
        if person_id is None:
            person = Person.objects.create(
                circle_id=circle_id, child_id=child_id, name=(display_name or '')[:NAME_MAX_LENGTH]
            )
            person_id = people[(circle_id, child_id)] = person.id
        tags.append(KeepPerson(keep_id=keep_id, person_id=person_id))
    KeepPerson.objects.bulk_create(tags, batch_size=500, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ('keeps', '0014_person_keepperson'),
    ]

    operations = [
        migrations.RunPython(backfill_people_from_children, migrations.RunPython.noop),
    ]
