import sys
from datetime import datetime
from importlib import import_module
from pathlib import Path

from loguru import logger
from sqlalchemy import URL, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

project_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(project_dir))

database = import_module("database", "database")
models = import_module("models", "database")
config = import_module("config").config


def get_engine() -> Engine | None:
    """
    Get engine to collect words from config.

    :return: sqlalchemy.engine.Engine object or None if database engine configured incorrect in the config
    """

    if config.COLLECT_WORDS_DB_NAME:
        return create_engine(
            URL.create(
                drivername="postgresql+psycopg",
                username=config.COLLECT_WORDS_DB_USER,
                password=config.COLLECT_WORDS_DB_PASSWORD,
                host=config.COLLECT_WORDS_DB_HOST,
                port=config.COLLECT_WORDS_DB_PORT,
                database=config.COLLECT_WORDS_DB_NAME,
            ),
            echo=config.DEBUG,
            pool_size=10
        )
    logger.info("Config variable config.COLLECT_WORDS_DB_NAME configured incorrectly.")
    return None


def collect_words(session_maker: sessionmaker, session_maker_to_collect: sessionmaker) -> None:
    """
    Collect words from one database to another.

    :param session_maker: Main database session maker
    :param session_maker_to_collect: To-collect database session maker
    """

    all_words = select(models.Word)
    with session_maker_to_collect() as lite_session:
        with session_maker() as main_session:
            all_words = main_session.execute(all_words).all()
            for word in all_words:
                w = word[0]
                word = models.Word(english=w.english, russian=w.russian, part_of_speech=w.part_of_speech)
                lite_session.add(word)
            lite_session.commit()


def main() -> None:
    logger.info("Start to collect words...")
    engine = get_engine()
    logger.info("Success get postgresql engine.")
    session_factory = sessionmaker(engine)
    todays_date = datetime.now().date().strftime('%Y-%m-%d')
    engine_to_collect = create_engine(
        f"sqlite:///collect_words_{todays_date}.db",
        echo=config.DEBUG,
        pool_size=10
    )
    logger.info(f"Success get engine for collect_words_{todays_date}.db sqlite database.")
    session_factory_to_collect = sessionmaker(engine_to_collect)
    models.Word.__table__.drop(engine_to_collect, checkfirst=True)
    models.Word.__table__.create(engine_to_collect)
    logger.info(f"Success reset collect_words_{todays_date}.db sqlite database.")
    collect_words(session_factory, session_factory_to_collect)
    logger.info("Ends collect words.")


if __name__ == "__main__":
    main()
