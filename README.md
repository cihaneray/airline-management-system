# Airline Management System

A Django REST Framework backend for managing airplanes, flights, and passenger reservations.

The project includes JWT authentication, PostgreSQL integration, Docker support, automated tests, a Postman Collection,
and CI/CD deployment to Google Cloud.

---

## Features

- Airplane CRUD operations
- Flight CRUD operations
- Reservation creation, update, listing, and cancellation
- JWT authentication
- PostgreSQL database
- Flight conflict validation
- Minimum one-hour gap between flights using the same airplane
- Flight capacity validation
- Automatic unique reservation-code generation
- Flight filtering, searching, ordering, and pagination
- Docker and Docker Compose
- Automated tests
- Postman Collection
- Google Cloud Compute Engine deployment
- Google Artifact Registry
- GitHub Actions CI/CD

---

## Technology Stack

- Python
- Django
- Django REST Framework
- PostgreSQL
- Simple JWT
- django-filter
- Gunicorn
- Nginx
- Docker
- Docker Compose
- GitHub Actions
- Google Cloud Compute Engine
- Google Artifact Registry
- Google Cloud Workload Identity Federation

---

## Project Structure

```text
airline-management/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy-gcp.yml
├── airline/
│   ├── migrations/
│   ├── tests/
│   ├── admin.py
│   ├── apps.py
│   ├── filters.py
│   ├── models.py
│   ├── serializers.py
│   ├── services.py
│   ├── urls.py
│   └── views.py
├── config/
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── nginx/
│   └── default.conf
├── postman/
│   ├── Airline Management API.postman_collection.json
│   └── Airline Local.postman_environment.json
├── scripts/
│   └── entrypoint.sh
├── .dockerignore
├── .env.example
├── compose.yaml
├── compose.prod.yaml
├── Dockerfile
├── manage.py
├── requirements.txt
└── README.md
```

---

# Local Setup

## 1. Clone the repository

```bash
git clone https://github.com/cihaneray/airline-management-system.git
cd airline-management
```

This is a private repository, authenticate with GitHub before cloning.

## 2. Create a virtual environment

Linux or macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

## 3. Install dependencies

Using pip:

```bash
pip install -r requirements.txt
```

Using uv:

```bash
uv sync
```

## 4. Create the environment file

Copy the example environment file:

Linux or macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Example local `.env`:

```env
DJANGO_SETTINGS_MODULE=config.settings

SECRET_KEY=replace-with-a-long-random-secret
DEBUG=True

ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1

POSTGRES_DB=airline_db
POSTGRES_USER=airline_user
POSTGRES_PASSWORD=replace-with-a-strong-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

---

# PostgreSQL Setup

Open PostgreSQL:

```bash
psql -U postgres
```

Create the database and user:

```sql
CREATE
DATABASE airline_db;

CREATE
USER airline_user
WITH PASSWORD 'replace-with-a-strong-password';

ALTER
DATABASE airline_db
OWNER TO airline_user;

GRANT ALL PRIVILEGES
ON DATABASE
airline_db
TO airline_user;
```

Connect to the database:

```sql
\c
airline_db
```

Grant schema permissions:

```sql
GRANT
ALL
ON SCHEMA public TO airline_user;
ALTER
SCHEMA public OWNER TO airline_user;
```

For local tests, allow the user to create a temporary test database:

```sql
ALTER
ROLE airline_user CREATEDB;
```

Exit PostgreSQL:

```sql
\q
```

---

# Database Migrations

Create migrations:

```bash
python manage.py makemigrations
```

Apply migrations:

```bash
python manage.py migrate
```

Using uv:

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
```

---

# Create an Admin User

```bash
python manage.py createsuperuser
```

Using uv:

```bash
uv run python manage.py createsuperuser
```

The Django admin panel is available at:

```text
http://localhost:8000/admin/
```

---

# Run the Development Server

```bash
python manage.py runserver
```

Using uv:

```bash
uv run python manage.py runserver
```

The API base URL is:

```text
http://localhost:8000/api
```

---

# Docker Usage

## Start development services

```bash
docker compose up --build
```

Run in the background:

```bash
docker compose up --build -d
```

Check running containers:

```bash
docker compose ps
```

View API logs:

```bash
docker compose logs -f api
```

Apply migrations:

```bash
docker compose exec api python manage.py migrate
```

Create a superuser:

```bash
docker compose exec api python manage.py createsuperuser
```

Run tests:

```bash
docker compose exec api python manage.py test airline.tests --verbosity=2
```

Stop services:

```bash
docker compose down
```

Remove services and local database volumes:

```bash
docker compose down -v
```

The last command permanently deletes the local PostgreSQL Docker volume.

---

# JWT Authentication

All airline endpoints require JWT authentication.

## Get access and refresh tokens

```http
POST /api/auth/token/
Content-Type: application/json
```

Request body:

```json
{
  "username": "admin",
  "password": "your-password"
}
```

Example response:

```json
{
  "refresh": "eyJ...",
  "access": "eyJ..."
}
```

## Send an authenticated request

Include the access token in the request header:

```http
Authorization: Bearer <access-token>
```

Example:

```http
GET /api/flights/
Authorization: Bearer eyJ...
```

## Refresh an access token

```http
POST /api/auth/token/refresh/
Content-Type: application/json
```

Request body:

```json
{
  "refresh": "eyJ..."
}
```

Example response:

```json
{
  "access": "new-access-token"
}
```

---

# API Endpoints

Base URL:

```text
http://localhost:8000/api
```

Production example:

```text
http://<vm-external-ip>/api
```

---

## Airplane Endpoints

### List airplanes

```http
GET /api/airplanes/
```

### Retrieve an airplane

```http
GET /api/airplanes/{id}/
```

### Create an airplane

```http
POST /api/airplanes/
```

Example request:

```json
{
  "tail_number": "TC-NRT",
  "model": "Airbus A320",
  "capacity": 180,
  "production_year": 2020,
  "status": true
}
```

### Update an airplane

```http
PATCH /api/airplanes/{id}/
```

Example request:

```json
{
  "status": false
}
```

### Delete an airplane

```http
DELETE /api/airplanes/{id}/
```

An airplane cannot be deleted when it is referenced by protected flight records.

### List flights assigned to an airplane

```http
GET /api/airplanes/{id}/flights/
```

Optional query parameters:

```text
upcoming=true
past=true
ordering=departure_time
ordering=-departure_time
```

### Airplane filtering examples

```text
GET /api/airplanes/?status=true
GET /api/airplanes/?model__icontains=airbus
GET /api/airplanes/?capacity__gte=150
GET /api/airplanes/?production_year__gte=2020
GET /api/airplanes/?search=TC-NRT
GET /api/airplanes/?ordering=-capacity
```

---

## Flight Endpoints

### List flights

```http
GET /api/flights/
```

### Retrieve a flight

```http
GET /api/flights/{id}/
```

### Create a flight

```http
POST /api/flights/
```

Example request:

```json
{
  "flight_number": "TK1901",
  "departure": "Istanbul Airport",
  "destination": "Heathrow Airport",
  "departure_time": "2027-08-10T10:00:00+03:00",
  "arrival_time": "2027-08-10T14:00:00+03:00",
  "airplane": 1
}
```

### Update a flight

```http
PATCH /api/flights/{id}/
```

Example request:

```json
{
  "destination": "Paris Charles de Gaulle Airport"
}
```

### Delete a flight

```http
DELETE /api/flights/{id}/
```

A flight cannot be deleted when it is referenced by protected reservation records.

### List reservations for a flight

```http
GET /api/flights/{id}/reservations/
```

Optional query parameters:

```text
status=true
status=false
search=passenger
ordering=created_at
ordering=-created_at
```

### Check flight availability

```http
GET /api/flights/{id}/availability/
```

Example response:

```json
{
  "flight_id": 1,
  "flight_number": "TK1901",
  "airplane_id": 1,
  "airplane_tail_number": "TC-NRT",
  "capacity": 180,
  "occupied_seats": 25,
  "available_seats": 155,
  "is_full": false
}
```

---

# Flight Filtering

Supported query parameters:

| Parameter             | Description                                |
|-----------------------|--------------------------------------------|
| `departure`           | Case-insensitive partial departure match   |
| `destination`         | Case-insensitive partial destination match |
| `airplane`            | Filter by airplane ID                      |
| `departure_date`      | Exact departure date                       |
| `departure_date_from` | Departure datetime lower limit             |
| `departure_date_to`   | Departure datetime upper limit             |
| `arrival_date`        | Exact arrival date                         |
| `arrival_date_from`   | Arrival datetime lower limit               |
| `arrival_date_to`     | Arrival datetime upper limit               |
| `upcoming`            | Future flights                             |
| `past`                | Departed flights                           |
| `available`           | Flights with remaining capacity            |

Examples:

```text
GET /api/flights/?departure=istanbul
GET /api/flights/?destination=london
GET /api/flights/?airplane=1
GET /api/flights/?departure_date=2027-08-10
GET /api/flights/?departure_date_from=2027-08-01T00:00:00Z
GET /api/flights/?departure_date_to=2027-08-31T23:59:59Z
GET /api/flights/?arrival_date=2027-08-10
GET /api/flights/?upcoming=true
GET /api/flights/?past=true
GET /api/flights/?available=true
GET /api/flights/?search=TK1901
GET /api/flights/?ordering=-departure_time
```

Filters can be combined:

```text
GET /api/flights/?departure=istanbul&destination=london&upcoming=true&available=true
```

---

## Reservation Endpoints

### List reservations

```http
GET /api/reservations/
```

### Retrieve a reservation

```http
GET /api/reservations/{id}/
```

### Create a reservation

```http
POST /api/reservations/
```

Example request:

```json
{
  "passenger_name": "Ayse Yilmaz",
  "passenger_email": "ayse@example.com",
  "flight": 1,
  "status": true
}
```

Example response:

```json
{
  "id": 1,
  "passenger_name": "Ayse Yilmaz",
  "passenger_email": "ayse@example.com",
  "reservation_code": "8K4P2QMX",
  "flight": 1,
  "status": true,
  "created_at": "2026-07-17T10:00:00Z"
}
```

The client cannot manually set `reservation_code` or `created_at`.

### Update a reservation

```http
PATCH /api/reservations/{id}/
```

Example request:

```json
{
  "passenger_name": "Ayse Yilmaz Updated"
}
```

### Cancel a reservation

```http
PATCH /api/reservations/{id}/cancel/
```

Reservations are canceled by setting `status` to `false`; they are not permanently deleted.

### Reservation filtering examples

```text
GET /api/reservations/?flight=1
GET /api/reservations/?status=true
GET /api/reservations/?created_at__date=2026-07-17
GET /api/reservations/?search=ayse@example.com
GET /api/reservations/?ordering=-created_at
```

---

# Business Rules

## Flight conflict validation

For flights assigned to the same airplane:

- Flight intervals cannot overlap.
- There must be at least one hour between the previous arrival and the next departure.
- The same schedule may be assigned to different airplanes.
- Inactive airplanes cannot be assigned to new flights.
- Arrival time must be later than departure time.
- Departure and destination cannot be the same.

Valid example:

```text
Existing flight: 10:00–14:00
New flight:      15:00–18:00
```

Invalid example:

```text
Existing flight: 10:00–14:00
New flight:      14:30–18:00
```

## Reservation capacity

- Only active reservations count toward capacity.
- A reservation cannot be created when the flight is full.
- Canceled reservations do not consume capacity.
- Reservation creation uses database transactions and row locking.

## Reservation codes

Reservation codes are:

- Generated automatically
- Unique
- Uppercase alphanumeric
- At least five characters
- Read-only for API clients

## Duplicate reservations

The same passenger email cannot have more than one active reservation for the same flight.

## Departed flights

A reservation cannot be created or reactivated for a flight that has already departed.

---

# Pagination

List endpoints may use page-number pagination.

Example:

```text
GET /api/flights/?page=2
```

Example response:

```json
{
  "count": 42,
  "next": "http://localhost:8000/api/flights/?page=2",
  "previous": null,
  "results": []
}
```

---

# HTTP Status Codes

|                   Status | Meaning                                                |
|-------------------------:|--------------------------------------------------------|
|                 `200 OK` | Request succeeded                                      |
|            `201 Created` | Resource created                                       |
|         `204 No Content` | Resource deleted                                       |
|        `400 Bad Request` | Invalid input or business-rule violation               |
|       `401 Unauthorized` | Missing, invalid, or expired JWT                       |
|          `403 Forbidden` | Authenticated but not permitted                        |
|          `404 Not Found` | Resource not found                                     |
| `405 Method Not Allowed` | HTTP method is not supported                           |
|           `409 Conflict` | Resource cannot be deleted because related data exists |

---

# Testing

Run all airline tests:

```bash
python manage.py test airline.tests --verbosity=2
```

Using uv:

```bash
uv run python manage.py test airline.tests --verbosity=2
```

Using Docker:

```bash
docker compose exec api python manage.py test airline.tests --verbosity=2
```

The test suite covers:

- JWT authentication
- Airplane CRUD
- Flight CRUD
- Flight conflict validation
- One-hour scheduling rule
- Filtering
- Flight availability
- Reservation code generation
- Capacity validation
- Duplicate reservations
- Reservation cancellation
- Protected deletion
- Service-layer behavior

---

# Postman

The repository includes:

```text
postman/Airline Management API.postman_collection.json
postman/Airline Local.postman_environment.json
```

## Import instructions

1. Open Postman.
2. Select **Import**.
3. Import both JSON files.
4. Select the **Airline Local** environment.
5. Update the username and password variables.
6. Run **Authentication → Obtain JWT Token**.
7. Create resources in this order:

```text
Airplane → Flight → Reservation
```

The Postman scripts automatically store:

- `access_token`
- `refresh_token`
- `airplane_id`
- `flight_id`
- `reservation_id`

For production testing, change:

```text
base_url=http://localhost:8000/api
```

to:

```text
base_url=http://<vm-external-ip>/api
```

---

# Google Cloud Deployment

The production environment uses:

- Google Compute Engine
- Google Artifact Registry
- Docker Compose
- PostgreSQL
- Gunicorn
- Nginx
- GitHub Actions
- Workload Identity Federation

## Deployment flow

```text
Push to main
    ↓
GitHub Actions CI
    ↓
Run tests
    ↓
Build Docker image
    ↓
Push commit-tagged image to Artifact Registry
    ↓
Connect to Compute Engine over SSH
    ↓
Pull the exact image
    ↓
Run Django checks and migrations
    ↓
Collect static files
    ↓
Recreate application containers
    ↓
Verify the deployed API
```

## Production environment file

The VM stores production variables at:

```text
/opt/airline/.env
```

Example:

```env
DJANGO_SETTINGS_MODULE=config.settings

SECRET_KEY=replace-with-a-production-secret
DEBUG=False

ALLOWED_HOSTS=34.77.138.60,localhost,127.0.0.1,api,nginx
CSRF_TRUSTED_ORIGINS=http://34.77.138.60

POSTGRES_DB=airline_db
POSTGRES_USER=airline_user
POSTGRES_PASSWORD=replace-with-a-strong-password
POSTGRES_HOST=db
POSTGRES_PORT=5432

GCP_PROJECT_ID=your-google-cloud-project-id
GCP_REGION=europe-west1
```
---

# CI/CD

## Continuous Integration

The CI workflow runs for pushes and pull requests.

It performs:

- Dependency installation
- Migration consistency check
- Django system checks
- Automated tests
- Docker image build validation

## Continuous Deployment

After CI succeeds on the `main` branch, the deployment workflow:

1. Authenticates to Google Cloud using Workload Identity Federation.
2. Builds the Docker image.
3. Tags the image with the tested commit SHA.
4. Pushes the image to Google Artifact Registry.
5. Copies the production Compose and Nginx files to the VM.
6. Pulls the exact commit-tagged image.
7. Runs Django system checks.
8. Verifies environment configuration.
9. Applies migrations.
10. Collects static files.
11. Recreates containers.
12. Verifies the running image.
13. Tests the API response.

## Required GitHub variables

```text
GCP_PROJECT_ID
GCP_PROJECT_NUMBER
GCP_REGION
GCP_ZONE
GCP_WORKLOAD_IDENTITY_PROVIDER
GCP_SERVICE_ACCOUNT
GCP_VM_NAME
```

## Required GitHub secrets

```text
GCP_VM_HOST
GCP_VM_USER
GCP_VM_SSH_PRIVATE_KEY
```

Never commit private keys or production credentials.

---

# Production Commands

Open the deployment directory:

```bash
cd /opt/airline
```

Check services:

```bash
docker compose   --env-file .env   --env-file .deploy.env   -f compose.prod.yaml   ps
```

View API logs:

```bash
docker compose   --env-file .env   --env-file .deploy.env   -f compose.prod.yaml   logs --tail=200 api
```

View Nginx logs:

```bash
docker compose   --env-file .env   --env-file .deploy.env   -f compose.prod.yaml   logs --tail=200 nginx
```

Check Django `ALLOWED_HOSTS`:

```bash
docker compose   --env-file .env   --env-file .deploy.env   -f compose.prod.yaml   exec api   python manage.py shell   -c "from django.conf import settings; print(settings.ALLOWED_HOSTS)"
```

Create a production superuser:

```bash
docker compose   --env-file .env   --env-file .deploy.env   -f compose.prod.yaml   exec api   python manage.py createsuperuser
```

---

# Common Problems

## HTTP 400 Bad Request

Check `ALLOWED_HOSTS`:

```env
ALLOWED_HOSTS=<vm-ip>,localhost,127.0.0.1,api,nginx
```

Then recreate the API container.

## HTTP 401 Unauthorized

This is expected when a protected endpoint is accessed without a valid JWT.

Get a token from:

```text
POST /api/auth/token/
```

## HTTP 502 or 504

Check the API container:

```bash
docker compose   --env-file .env   --env-file .deploy.env   -f compose.prod.yaml   ps -a
```

Check API logs:

```bash
docker compose   --env-file .env   --env-file .deploy.env   -f compose.prod.yaml   logs --tail=200 api
```

## Test database permission error

For local development:

```sql
ALTER
ROLE airline_user CREATEDB;
```

## Artifact Registry pull error

Verify:

- The VM service account has `roles/artifactregistry.reader`.
- Docker authentication is configured.
- The repository and region are correct.
- The requested image tag exists.

---

# Security Notes

- Keep `DEBUG=False` in production.
- Never commit `.env`.
- Never commit SSH private keys.
- Do not expose PostgreSQL port `5432`.
- Use strong secrets and passwords.
- Restrict SSH access.
- Use HTTPS in a real production environment.
- Use Workload Identity Federation instead of long-lived service-account keys.
- Back up the production database regularly.

---

# License

This repository has been developed as a Technical Case Study for an ongoing recruitment process.
