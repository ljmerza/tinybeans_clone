docker compose exec web python manage.py test
docker compose exec web python manage.py test --settings=mysite.test_settings

docker compose exec web python manage.py migrate

docker compose up --build


http://192.168.1.76:8000/api/docs
http://192.168.1.76:5556/flower

todo:
- maybe make some view files smaller?
- add pagination to list returning apis (ie return all members for circle)
- add max limits to adding members to circle and whatever else
- add more indexes to db tables for performance
- add more logging to important actions
- add rate limiting to important apis
- favorite moments for each user (whats favorite for child?)
  - make favorite moments a model not json on user
- allow adding pictures, videos, audio, notes
- who can add moments? admin, member, any user?
- add more fields to moment - location, tags, etc
- add search to moments - by tags, location, date range, text in notes
- a moment can have users in it - tagged users
- user can have favorite moments