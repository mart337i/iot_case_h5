from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Set the DATABASE_URL, you will need to update this with your actual database credentials
DATABASE_URL = "postgresql+asyncpg://sysadmin:Vds79bzw-@localHost:5432/app?prepared_statement_cache_size=0"

# Create the async engine
engine = create_async_engine(
   DATABASE_URL,
   echo=True,
   future=True
)

# Create the async sessionmaker
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

