import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from supabase import create_client, Client


# Load .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PORT = int(os.getenv("PORT", "8000"))


# Check environment variables
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_KEY must be set in .env"
    )


# Create Supabase client
supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# Create FastAPI app
app = FastAPI(
    title="Auth Login & Protect API",
    description="Authentication API using FastAPI and Supabase",
    version="1.0.0"
)


# Request model
class AuthRequest(BaseModel):
    email: str
    password: str


# Test route
@app.get("/")
def root():
    return {
        "message": "Auth Login & Protect API is running"
    }


# -------------------------
# SIGNUP
# -------------------------

@app.post("/auth/signup", status_code=201)
def signup(credentials: AuthRequest):

    # Check for empty fields
    if not credentials.email.strip() or not credentials.password.strip():
        return JSONResponse(
            status_code=400,
            content={
                "error": "Email and password are required"
            }
        )

    try:
        response = supabase.auth.sign_up({
            "email": credentials.email,
            "password": credentials.password
        })

        return {
            "user": (
                response.user.model_dump()
                if response.user
                else None
            )
        }

    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Unable to create account"
            }
        )


# -------------------------
# LOGIN
# -------------------------

@app.post("/auth/login", status_code=200)
def login(credentials: AuthRequest):

    # Check for empty fields
    if not credentials.email.strip() or not credentials.password.strip():
        return JSONResponse(
            status_code=400,
            content={
                "error": "Email and password are required"
            }
        )

    try:
        response = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })

        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token
        }

    except Exception:
        return JSONResponse(
            status_code=401,
            content={
                "error": "Invalid login credentials"
            }
        )


# -------------------------
# AUTHENTICATION DEPENDENCY
# -------------------------

def verify_token(authorization: str | None = Header(default=None)):
    if not authorization:
        return JSONResponse(
            status_code=401,
            content={
                "error": "Invalid or expired token"
            }
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return JSONResponse(
            status_code=401,
            content={
                "error": "Invalid or expired token"
            }
        )

    token = parts[1]

    try:
        response = supabase.auth.get_user(token)
        if not response.user:
            raise ValueError("Supabase did not return a user")

        return {
            "token": token,
            "user": response.user
        }
    except Exception:
        return JSONResponse(
            status_code=401,
            content={
                "error": "Invalid or expired token"
            }
        )


# -------------------------
# PROTECTED PROFILE
# -------------------------

@app.get("/protected/profile")
def protected_profile(auth=Depends(verify_token)):
    return auth["user"].model_dump()


# -------------------------
# PROTECTED DASHBOARD
# -------------------------

@app.get("/protected/dashboard")
def protected_dashboard(auth=Depends(verify_token)):
    return {
        "message": "Welcome to your dashboard",
        "user": auth["user"].model_dump()
    }


# -------------------------
# LOGOUT
# -------------------------

@app.post("/auth/logout", status_code=204)
def logout(auth=Depends(verify_token)):
    supabase.auth.sign_out(auth["token"])
    return Response(status_code=204)


# -------------------------
# RUN SERVER
# -------------------------

if __name__ == "__main__":
    import uvicorn

    print("Server running and connected to Supabase")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True
    )

    