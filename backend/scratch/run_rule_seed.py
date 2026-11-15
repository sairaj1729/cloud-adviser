import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.rule_engine.registry import RuleRegistry
from app.rule_engine.engine import RuleEngine

async def run():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    # 1. Seed rules
    await RuleRegistry.seed_rules(db, replace_existing=True)
    rule_count = await db.rules.count_documents({})
    print(f"Total active rules in db.rules: {rule_count}")
    
    # 2. Re-evaluate RuleEngine across accounts
    user = await db.users.find_one({"email": "jordan@acme.io"})
    user_id = str(user["_id"])
    accounts = await db.cloud_accounts.find({"user_id": user_id}).to_list(length=10)
    
    engine = RuleEngine(db)
    total_findings = 0
    total_savings = 0.0
    for acc in accounts:
        res = await engine.evaluate_account(user_id, str(acc["_id"]))
        prov = acc.get("provider", "").upper()
        name = acc.get("display_name", "")
        print(f"Account {prov} ({name}): {res['findings_created']} findings, ${res['estimated_monthly_savings']}/mo")
        total_findings += res["findings_created"]
        total_savings += res["estimated_monthly_savings"]
        
    findings_in_db = await db.findings.count_documents({})
    print(f"\nTotal findings stored in db.findings collection: {findings_in_db}")
    print(f"Total monthly savings: ${total_savings:.2f}/mo")
    client.close()

if __name__ == "__main__":
    asyncio.run(run())
