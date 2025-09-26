docker compose exec web python manage.py test

docker compose exec web python manage.py migrate


http://192.168.1.76:8000/api/docs
http://192.168.1.76:5556/flower