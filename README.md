docker compose exec web python manage.py test

docker compose exec web python manage.py migrate

docker compose up --build


http://192.168.1.76:8000/api/docs
http://192.168.1.76:5556/flower

todo:
- consolidate `mysite/users/views/utils.py` and `mysite/users/token_utils.py`
- maybe make some view files smaller?
- add more tests
- remove pycache files