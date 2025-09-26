from django.http import HttpResponse


def index(request):
    """Return a simple hello world response."""
    return HttpResponse("Hello, world! You're at the main index.")
