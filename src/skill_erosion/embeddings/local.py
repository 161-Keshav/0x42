"""The genuine Chroma ONNX embedding function. No substitute or fallback."""
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
MODEL_VERSION="all-MiniLM-L6-v2-onnx/chroma-default-v1"
def embedding_function(): return DefaultEmbeddingFunction()
