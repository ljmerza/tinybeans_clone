docker compose exec web python manage.py test
docker compose exec web python manage.py test --settings=mysite.test_settings

docker compose exec web python manage.py migrate

docker compose up --build


http://192.168.1.76:8000/api/docs
http://192.168.1.76:5556/flower

todo:
- maybe make some view files smaller?
- fix tests and make sure tests are useful and not bloated
- add pagination to list returning apis (ie return all members for circle)
- add max limits to adding members to circle and whatever else
- add more indexes to db tables for performance