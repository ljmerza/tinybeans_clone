from django.test import TestCase, Client
from django.urls import reverse
from django.http import HttpResponse


class MainViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_index_view_returns_hello_world(self):
        """Test that the main index view returns a simple hello world message."""
        response = self.client.get(reverse('index'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.content.decode(), "Hello, world! You're at the main index.")
