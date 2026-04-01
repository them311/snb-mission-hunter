"""
SNB Mission Hunter — Configuration centralisée.
Toutes les variables d'environnement sont lues ici.
"""

import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # --- Anthropic ---
    anthropic_api_key: str = ""

    # --- Supabase ---
    supabase_url: str = ""
    supabase_service_key: str = ""

    # --- Telegram ---
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # --- Email ---
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_to: str = ""

    # --- Agent ---
    score_threshold: int = 70
    scan_interval_fast: int = 300  # 5 min — Tier 1
    scan_interval_slow: int = 1800  # 30 min — Tier 2
    log_level: str = "INFO"

    # --- Profil actif (Baptiste par défaut) ---
    active_profile: str = "baptiste"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            supabase_url=os.getenv("SUPABASE_URL", "https://vcchtbjfugzoyzzxbugs.supabase.co"),
            supabase_service_key=os.getenv("SUPABASE_SERVICE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZjY2h0YmpmdWd6b3l6enhidWdzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTA0NTU5NSwiZXhwIjoyMDkwNjIxNTk1fQ.v5eiplTJhUZsUkb1tbFma6vwnuoCZzM6y4a71SSjcWI"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_user=os.getenv("SMTP_USER", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            email_to=os.getenv("EMAIL_TO", ""),
            score_threshold=int(os.getenv("SCORE_THRESHOLD", "70")),
            scan_interval_fast=int(os.getenv("SCAN_INTERVAL_FAST", "300")),
            scan_interval_slow=int(os.getenv("SCAN_INTERVAL_SLOW", "1800")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            active_profile=os.getenv("ACTIVE_PROFILE", "baptiste"),
        )

    def validate(self) -> List[str]:
        """Retourne la liste des variables manquantes critiques."""
        errors = []
        if not self.supabase_url:
            errors.append("SUPABASE_URL")
        if not self.supabase_service_key:
            errors.append("SUPABASE_SERVICE_KEY")
        if not self.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY")
        return errors


# Profils S&B
PROFILES = {
    "baptiste": {
        "name": "Baptiste Thévenot",
        "email": "bp.thevenot@gmail.com",
        "phone": "06 86 50 43 79",
        "linkedin": "linkedin.com/in/baptiste-thevenot-64275777",
        "siret": "849 022 058",
        "address": "10 chemin de Catala, 31100 Toulouse",
        "languages": ["fr", "en", "es"],
        "formation": "Master 2 Stratégie & Conseil — TBS | Stanford Online IA/ML",
        "keywords": [
            "react", "next.js", "nextjs", "shopify", "liquid", "e-commerce", "ecommerce",
            "claude", "anthropic", "gpt", "openai", "chatbot", "ia", "ai",
            "intelligence artificielle", "automatisation", "automation", "workflow",
            "n8n", "make", "zapier", "scraping", "python", "data", "dashboard",
            "analytics", "stratégie digitale", "transformation digitale",
            "conduite du changement", "branding", "brand", "identité visuelle",
            "charte graphique", "ux", "ui", "seo", "audit", "optimisation",
            "performance", "site web", "website", "landing page", "webdesign",
            "api", "integration", "mcp", "agent", "multi-agent",
            "typescript", "html", "css", "javascript", "netlify", "railway",
        ],
        "tjm_min": 350,
        "tjm_standard": 450,
        "tjm_expert": 600,
        "portfolio": [
            "La Française des Sauces — marque alimentaire premium, site Shopify complet, branding A-Z",
            "Chef IA — configurateur recettes interactif 3D avec IA",
            "Système multi-agents IA — 6 agents spécialisés, Claude API + Shopify MCP",
            "S&B Consulting Platform — SPA React, agrégation missions, facturation, chat IA",
            "Audit cybersécurité — audit 936 comptes, migration Bitwarden",
        ],
    },
    "sacha": {
        "name": "Sacha Zekri",
        "email": "zekrisacha@gmail.com",
        "keywords": [],
        "tjm_min": 300,
        "tjm_standard": 400,
        "tjm_expert": 500,
        "portfolio": [],
    },
}
