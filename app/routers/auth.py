from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import User, UserRole
from ..schemas import LoginRequest, TokenResponse, UserCreate, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["Auth"])


def _authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    return user


def _token_response(user: User) -> TokenResponse:
    token = create_access_token(user.id, user.role.value)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role=user.role,
        user_id=user.id,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """Create a buyer or seller account and return an access token."""
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    user = User(
        name=payload.name.strip(),
        email=email,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, db: Session = Depends(get_db)):
    """
    Login endpoint supporting BOTH multipart/form-data (FormData) and application/json.
    Accepts 'username' or 'email' alongside 'password'.
    """
    content_type = request.headers.get("content-type", "")
    role = None

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        email = str(form.get("username") or form.get("email") or "").strip()
        password = str(form.get("password") or "")
        role = form.get("role")
    else:
        try:
            body = await request.json()
            email = str(body.get("username") or body.get("email") or "").strip()
            password = str(body.get("password") or "")
            role = body.get("role")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid request body")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and Password are required")

    user = _authenticate(db, email, password)
    if role and user.role.value != str(role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This account is not registered as a {role}",
        )
    return _token_response(user)


@router.post("/login/buyer", response_model=TokenResponse)
def login_buyer(payload: LoginRequest, db: Session = Depends(get_db)):
    """Buyer-only login."""
    email = (payload.username or payload.email or "").strip()
    return _token_response(_authenticate(db, email, payload.password))


@router.post("/login/seller", response_model=TokenResponse)
def login_seller(payload: LoginRequest, db: Session = Depends(get_db)):
    """Seller-only login."""
    email = (payload.username or payload.email or "").strip()
    return _token_response(_authenticate(db, email, payload.password))


@router.post("/token", response_model=TokenResponse, include_in_schema=True)
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 form login (used by the Swagger 'Authorize' button). Use email as username."""
    return _token_response(_authenticate(db, form.username, form.password))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    """Return the currently logged-in user."""
    return user
