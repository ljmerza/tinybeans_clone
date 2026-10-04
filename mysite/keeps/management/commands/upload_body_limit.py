"""Print the largest upload request body the app accepts, in bytes.

docker/entrypoint.sh writes this into the image's nginx `client_max_body_size`,
so nginx never rejects an upload the app would take (or explain).
"""

from django.core.management.base import BaseCommand

from mysite.keeps.views.uploads import max_upload_request_size


class Command(BaseCommand):
    help = "Print the largest upload request body (bytes) for the reverse proxy's body-size cap."

    def handle(self, *args, **options):
        self.stdout.write(str(max_upload_request_size()))
