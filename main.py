from app import create_app
from prometheus_fastapi_instrumentator import Instrumentator
app = create_app()
#Monitoring
Instrumentator().instrument(app).expose(app)
