# Tinybeans Copy

## Quick Start

```bash
# Start all services (web, postgres, redis, celery, flower)
docker compose up --build

# Run migrations (if needed)
docker compose exec web python manage.py migrate

# Run tests (no external services required - uses in-memory cache/broker)
docker compose exec web python manage.py test --settings=mysite.test_settings

# Or run tests locally without Docker
python manage.py test --settings=mysite.test_settings
```

## Links
- http://localhost:8000/api/docs
- http://localhost:4100

## Development Notes

### TODO:
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