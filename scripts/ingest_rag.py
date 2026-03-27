"""
NirovaAI — RAG Knowledge Base Ingestion
=========================================
Run this ONCE after setting up MongoDB to load medical knowledge.

Usage:
    cd nirovaai_final
    python scripts/ingest_rag.py

What it does:
    1. Loads sample Bangladesh medical knowledge
    2. Embeds each chunk using multilingual model
    3. Stores in MongoDB knowledge_chunks collection
    4. RAG chat will then use this for grounded responses
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from motor.motor_asyncio import AsyncIOMotorClient
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB  = os.getenv("MONGODB_DB_NAME", "nirovaai")

# Bangladesh medical knowledge base
KNOWLEDGE_BASE = [
    {
        "content": """Dengue fever is a mosquito-borne viral infection common in Bangladesh,
        especially during monsoon season (June-October). Symptoms include sudden high fever
        (103-104°F), severe headache, pain behind the eyes, muscle and joint pain, nausea,
        vomiting, and skin rash. Warning signs include severe abdominal pain, persistent
        vomiting, bleeding from gums or nose, and rapid breathing. Treatment: rest, ORS,
        paracetamol (avoid aspirin/ibuprofen). NS1 antigen test confirms dengue in first 5 days.
        IgG and IgM antibody tests for later stages.""",
        "source": "WHO Bangladesh Dengue Guidelines",
        "category": "dengue"
    },
    {
        "content": """Typhoid fever is caused by Salmonella typhi, transmitted through
        contaminated food and water. Common in Bangladesh due to poor sanitation in some areas.
        Symptoms: sustained fever (103-104°F), weakness, stomach pain, headache, loss of
        appetite, constipation or diarrhea. Widal test and blood culture confirm diagnosis.
        Treatment: ciprofloxacin or azithromycin for 7-14 days. Prevention: safe water,
        food hygiene, typhoid vaccine available in Bangladesh.""",
        "source": "WHO Typhoid Guidelines",
        "category": "typhoid"
    },
    {
        "content": """Tuberculosis (TB) remains a major health challenge in Bangladesh.
        Symptoms: persistent cough for 3+ weeks, chest pain, coughing up blood, weakness,
        weight loss, night sweats, fever. Diagnosis: sputum test, chest X-ray, GeneXpert.
        Treatment: 6-month antibiotic course (DOTS program) available FREE at government
        health centers across Bangladesh. Drug-resistant TB is increasing.""",
        "source": "IEDCR TB Report Bangladesh",
        "category": "tuberculosis"
    },
    {
        "content": """Arsenicosis in Bangladesh: approximately 20 million people exposed to
        arsenic-contaminated groundwater. Most affected districts: Comilla, Noakhali, Chandpur,
        Munshiganj, Faridpur. Symptoms develop after 5-10 years: skin lesions (melanosis,
        keratosis), peripheral neuropathy, increased cancer risk. Prevention: use surface water
        or deep tube wells, water filters. Eat nutritious diet rich in protein and vegetables.""",
        "source": "WHO Bangladesh Arsenicosis Report",
        "category": "arsenicosis"
    },
    {
        "content": """Malaria in Bangladesh is endemic in Chittagong Hill Tracts.
        Symptoms: fever with chills and sweating (often cyclical), headache, muscle pain,
        fatigue, nausea, vomiting. Falciparum malaria can cause cerebral malaria — a medical
        emergency. Diagnosis: rapid test (RDT) or blood smear. Treatment: artemisinin-based
        combination therapy (ACT) available FREE at government hospitals. Prevention:
        insecticide-treated bed nets.""",
        "source": "IEDCR Malaria Guidelines Bangladesh",
        "category": "malaria"
    },
    {
        "content": """Paracetamol (Napa, Ace, Pyralex): for fever and mild pain.
        Adults: 500-1000mg every 4-6 hours, maximum 4g per day.
        NEVER exceed recommended dose — overdose causes severe liver damage.
        Avoid alcohol when taking paracetamol.
        Safe during pregnancy at recommended doses.
        For dengue fever: ONLY use paracetamol, NOT ibuprofen or aspirin.""",
        "source": "Bangladesh Drug Reference",
        "category": "medication"
    },
    {
        "content": """ORS (Oral Rehydration Solution) is critical for dehydration in Bangladesh.
        Available at every pharmacy as Saline or ORS packets.
        For adults: dissolve 1 packet in 1 liter of clean water.
        Give small sips frequently for vomiting patients.
        Homemade ORS: 1 liter water + 6 teaspoons sugar + 0.5 teaspoon salt.
        Essential for dengue, diarrhea, cholera, and any fever with sweating.""",
        "source": "DGHS Bangladesh Hydration Guidelines",
        "category": "treatment"
    },
    {
        "content": """ডেঙ্গু জ্বরের লক্ষণ: হঠাৎ তীব্র জ্বর, মাথাব্যথা, চোখের পেছনে ব্যথা,
        শরীর ও গিরায় ব্যথা, বমি বমি ভাব, শরীরে র‌্যাশ।
        বিপদের লক্ষণ: পেটে তীব্র ব্যথা, ক্রমাগত বমি, রক্তক্ষরণ, শ্বাসকষ্ট।
        করণীয়: পর্যাপ্ত পানি ও ORS পান, প্যারাসিটামল খান।
        NS1 পরীক্ষা করান। বিপদের লক্ষণে অবিলম্বে হাসপাতালে যান।
        আইবুপ্রোফেন বা অ্যাসপিরিন খাবেন না।""",
        "source": "DGHS Bangladesh Bangla Health Guide",
        "category": "dengue_bangla"
    },
    {
        "content": """When to go to hospital IMMEDIATELY in Bangladesh:
        - Fever above 103°F that doesn't reduce with paracetamol
        - Difficulty breathing or shortness of breath
        - Chest pain
        - Severe abdominal pain
        - Bleeding from any site
        - Confusion, seizures, or loss of consciousness
        - Signs of dehydration: no urination for 6+ hours, sunken eyes
        - Rash spreading rapidly
        Nearest emergency: Any government district hospital is free.""",
        "source": "Bangladesh Emergency Health Guidelines",
        "category": "emergency"
    },
    {
        "content": """Kala-azar (Visceral Leishmaniasis) is endemic in northern Bangladesh,
        especially Mymensingh, Rajshahi, Rangpur divisions. Transmitted by sandfly bites.
        Symptoms: prolonged fever (weeks to months), weight loss, weakness, enlarged spleen
        and liver, darkening of skin. Diagnosis: rK39 rapid test. Treatment: FREE at
        government hospitals — amphotericin B or miltefosine. Bangladesh aims to eliminate
        kala-azar by 2030.""",
        "source": "IEDCR Kala-azar Bangladesh",
        "category": "kala_azar"
    }
]


async def ingest():
    log.info("=" * 55)
    log.info("NirovaAI — Loading RAG Knowledge Base")
    log.info("=" * 55)

    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DB]
    collection = db["knowledge_chunks"]

    await client.admin.command("ping")
    log.info("✅ MongoDB connected")

    # Load embedding model
    log.info("Loading embedding model...")
    embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    log.info("✅ Embedder ready")

    # Clear existing knowledge
    count = await collection.count_documents({})
    if count > 0:
        await collection.delete_many({})
        log.info(f"Cleared {count} existing chunks")

    # Embed and store each chunk
    log.info(f"Embedding {len(KNOWLEDGE_BASE)} knowledge chunks...")
    documents = []
    for chunk in KNOWLEDGE_BASE:
        embedding = embedder.encode(
            chunk["content"],
            normalize_embeddings=True
        ).tolist()

        documents.append({
            "content": chunk["content"],
            "source": chunk["source"],
            "category": chunk["category"],
            "embedding": embedding
        })

    await collection.insert_many(documents)
    log.info(f"✅ {len(documents)} chunks stored in MongoDB")

    # Create text index for keyword search fallback
    await collection.create_index([("content", "text")])
    log.info("✅ Text search index created")

    log.info("=" * 55)
    log.info("✅ RAG Knowledge Base Ready!")
    log.info(f"   Collection: {MONGODB_DB}.knowledge_chunks")
    log.info(f"   Chunks: {len(documents)}")
    log.info("=" * 55)
    log.info("")
    log.info("OPTIONAL: Add Vector Search in Atlas for better results:")
    log.info("Atlas → knowledge_chunks → Search Indexes → Create Index")
    log.info('JSON: {"mappings":{"dynamic":true,"fields":{"embedding":')
    log.info('       {"dimensions":384,"similarity":"cosine","type":"knnVector"}}}}')

    client.close()


if __name__ == "__main__":
    asyncio.run(ingest())
