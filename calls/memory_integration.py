from mem0 import Memory
from dotenv import load_dotenv

load_dotenv()


config = {
    "embedder": {
        "provider": "huggingface",
        "config": {
            "model": "l3cube-pune/indic-sentence-similarity-sbert",
        }
    },
    "llm": {
        "provider": "sarvam",
        "config": {
            "model": "sarvam-m",
            "temperature": 0.2,
        }
    },
   "vector_store": {
        "provider": "qdrant",
        "config": {
            "embedding_model_dims": 768
        }
    }
}

def init_memory():
    m = Memory.from_config(config)
    return m