The admin user list api is not showing the data accuartly: like evern suer subbimited the kusy the staus its return not submitted like that we need to mad eeach returned data fuield one by one in each flow and figure out the gaps and issue 

Docker contxt:
PS UserBackend> 
 *  History restored 

PS UserBackend> docker compose up -d
[+] Running 9/9
 ✔ Container cg-migrations-local     Started                                           5.8s 
 ✔ Container cg-collectstatic-local  Started                                           5.8s 
 ✔ Container cg-fixtures-local       Started                                           5.2s 
 ✔ Container cg-api-local            Started                                           5.0s 
 ✔ Container cg-celery-local         Started                                           3.3s 
 ✔ Container cg-db-local             Started                                           0.6s 
 ✔ Container cg-redis-local          Started                                           0.5s 
 ✔ Container cg-rabbitmq-local       Started                                           0.6s 
 ✔ Container cg-pgbouncer-local      Started                                           0.4s 
PS UserBackend> docker ps
CONTAINER ID   IMAGE                      COMMAND                  CREATED          STATUS         PORTS                                             NAMES
4a357abefeff   cg-api:local               "make run.celery.prod"   6 seconds ago    Up 3 seconds                                                     cg-celery-local
98aee0fb42f2   cg-api:local               "sh -c 'uv run manag…"   8 seconds ago    Up 3 seconds   0.0.0.0:8010->80/tcp, [::]:8010->80/tcp           cg-api-local
84bdd00f5f96   cg-api:local               "make loadfixtures"      9 seconds ago    Up 3 seconds                                                     cg-fixtures-local
dedf78b96c5e   cg-api:local               "make migrate"           10 seconds ago   Up 4 seconds                                                     cg-migrations-local
89cf76881761   cg-api:local               "make collectstatic"     10 seconds ago   Up 4 seconds                                                     cg-collectstatic-local
58338230dfa8   edoburu/pgbouncer:latest   "/entrypoint.sh /usr…"   24 hours ago     Up 4 seconds   5432/tcp                                          cg-pgbouncer-local
8219c8ce22a1   postgres:16                "docker-entrypoint.s…"   24 hours ago     Up 5 seconds   5432/tcp                                          cg-db-local
6b47645cf995   rabbitmq:3.13-management   "docker-entrypoint.s…"   24 hours ago     Up 5 seconds   0.0.0.0:15672->15672/tcp, [::]:15672->15672/tcp   cg-rabbitmq-local
394704cd0b4a   redis:latest               "docker-entrypoint.s…"   24 hours ago     Up 5 seconds   0.0.0.0:6380->6379/tcp, [::]:6380->6379/tcp       cg-redis-local
PS UserBackend> 


Testing for api endpoints:
curl -X 'POST' \
  'http://localhost:8010/api/admin/login' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -H 'X-CSRFTOKEN: vuascYwGKzXzqU0lYokgpgzM2pDnT8QIRjfHwZ3uvOpEcK8BQQwkHM1fgPN1EZrw' \
  -F 'email=janak@powerbank.com' \
  -F 'password=5060'
Request URL
http://localhost:8010/api/admin/login
Server response
Code	Details
200	
Response body
Download
{
  "success": true,
  "message": "Admin login successful",
  "data": {
    "user_id": "1",
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc5Nzc1NDU2LCJpYXQiOjE3NzcxODM0NTYsImp0aSI6IjBmYmJjNTMxODlmYTQ0ZDA5Njc3NzRiYmQzZWE1OWQ4IiwidXNlcl9pZCI6IjEiLCJpc3MiOiJDaGFyZ2VHaGFyLUFQSSJ9.8A9_Y8cXMRDxXfEePAS6krPHQ3kPd0dzZ5uwvi9Ad2c",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc4NDk1OTQ1NiwiaWF0IjoxNzc3MTgzNDU2LCJqdGkiOiI2M2ZiOGQxY2I2YzM0YTNjYjBkM2NkYmM4MmQxZDUwOSIsInVzZXJfaWQiOiIxIiwiaXNzIjoiQ2hhcmdlR2hhci1BUEkifQ.AqSK_B04Nq7IrO6XsyxtP3TrZgO-B03uaJhyGSkuxVc",
    "user": {
      "id": "1",
      "email": "janak@powerbank.com",
      "username": "janak",
      "is_staff": true,
      "is_superuser": true,
      "role": "super_admin"
    },
    "message": "Admin login successful"
  }
}