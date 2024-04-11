from sqlalchemy.ext.asyncio import create_async_engine

# DATABASE_URL = os.environ.get("")
DATABASE_URL = "postgresql+asyncpg://sysadmin:admin1234@localHost:5432/app?prepared_statement_cache_size=0"

engine = create_async_engine(
   DATABASE_URL,
   echo=True,
   future=True
)

