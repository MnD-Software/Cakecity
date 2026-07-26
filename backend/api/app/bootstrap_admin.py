"""Create or promote the first Cake City administrator from deployment secrets.

Run once with ADMIN_EMAIL and ADMIN_PASSWORD in the environment. The password is
hashed by the same scrypt policy as customer credentials and is never printed.
"""
import asyncio
import os
from sqlalchemy import select
from .auth import hash_password
from .database import SessionFactory
from .models import AuditEvent, Customer


async def bootstrap() -> None:
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    first_name = os.environ.get("ADMIN_FIRST_NAME", "Cake City").strip()
    if not email or not password:
        raise RuntimeError("ADMIN_EMAIL and ADMIN_PASSWORD are required")
    async with SessionFactory() as db:
        customer = await db.scalar(select(Customer).where(Customer.email == email))
        if customer:
            customer.role = "admin"
            customer.is_active = True
            customer.password_hash = hash_password(password)
        else:
            customer = Customer(
                email=email, password_hash=hash_password(password),
                first_name=first_name, last_name="Admin", role="admin",
            )
            db.add(customer)
        await db.flush()
        db.add(AuditEvent(
            actor_id=customer.id, action="staff.admin_bootstrapped",
            target_type="customer", target_id=str(customer.id),
            changes={"role": "admin", "email": email},
        ))
        await db.commit()
    print(f"Administrator ready: {email}")


if __name__ == "__main__":
    asyncio.run(bootstrap())
