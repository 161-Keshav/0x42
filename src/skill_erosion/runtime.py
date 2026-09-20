from skill_erosion.config import data_dir
from skill_erosion.storage.sqlite_repo import SQLiteRepository
from skill_erosion.embeddings.chroma import ChromaStore
from skill_erosion.orchestration.pipeline import Pipeline

def create_pipeline(root=None):
    root=root or data_dir()
    return Pipeline(SQLiteRepository(root/"processed/skill_erosion.sqlite"),ChromaStore(root/"processed/chroma"))
