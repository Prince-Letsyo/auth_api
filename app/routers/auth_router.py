from app.routers.base import CustomRouter


auth_router: CustomRouter = CustomRouter(prefix="/auth", tags=["auth"])
