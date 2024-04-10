from sqlmodel import create_engine, SQLModel

# DATABASE_URL = os.environ.get("")
DATABASE_URL = "postgresql://sysadmin:admin1234@localHost:5432/app"
engine = create_engine(DATABASE_URL, echo=True)


def init_db():
    SQLModel.metadata.create_all(engine)

