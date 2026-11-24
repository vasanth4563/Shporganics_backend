from fastapi import APIRouter, Depends

from ..deps import require_buyer, require_seller
from ..models import User

router = APIRouter(prefix="/api", tags=["Role protected"])


@router.get("/buyer/dashboard")
def buyer_dashboard(user: User = Depends(require_buyer)):
    """Accessible only with a buyer access token."""
    return {"message": f"Welcome {user.name}! This is the buyer dashboard.", "role": user.role}


@router.get("/seller/dashboard")
def seller_dashboard(user: User = Depends(require_seller)):
    """Accessible only with a seller access token."""
    return {"message": f"Welcome {user.name}! This is the seller dashboard.", "role": user.role}
