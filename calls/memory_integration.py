try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    print("Warning: mem0 not available - memory features will be disabled")

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
    if not MEM0_AVAILABLE:
        print("Warning: Memory functionality disabled - mem0 not available")
        return None
    
    try:
        m = Memory.from_config(config)
        return m
    except Exception as e:
        print(f"Warning: Failed to initialize memory system: {e}")
        return None