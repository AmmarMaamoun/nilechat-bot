"""Create the demo client (عقارات جميلة) and print its widget api_key.

Run once:  python seed_demo.py
Re-running updates the knowledge base instead of creating a duplicate.
The listings below are SAMPLE data for demos — replace with the client's real info.
"""
import asyncio
from db import get_pool, list_companies, create_company, update_company_knowledge, get_company_by_id

NAME = "عقارات جميلة"

WELCOME = "أهلاً بيك في عقارات جميلة 🏡 أقدر أساعدك تلاقي شقتك أو فيلتك. بتدور على إيه؟"

KNOWLEDGE = """
عقارات جميلة — شركة تسويق عقاري في القاهرة الجديدة والشيخ زايد.
مواعيد العمل: من السبت للخميس، من 10 الصبح لحد 8 بالليل. الجمعة إجازة.
رقم التليفون والواتساب: 01000000000
العنوان: التجمع الخامس، شارع التسعين الشمالي، مبنى 12.

الوحدات المتاحة:
1) شقة في التجمع الخامس — 150 متر، 3 أوض، 2 حمام، تشطيب كامل. السعر 6,500,000 جنيه. مقدم 10% وتقسيط على 7 سنين.
2) شقة في مدينتي — 120 متر، 2 أوضة، 2 حمام، نص تشطيب. السعر 4,200,000 جنيه. مقدم 15% وتقسيط على 6 سنين.
3) دوبلكس في الشيخ زايد — 220 متر، 4 أوض، 3 حمام، جاردن 80 متر. السعر 11,000,000 جنيه. مقدم 20% وتقسيط على 5 سنين.
4) فيلا تاون هاوس في الشيخ زايد — 280 متر، 4 أوض، 4 حمام. السعر 16,500,000 جنيه. كاش أو تقسيط على 4 سنين.
5) شقة إيجار في التجمع — 130 متر، مفروشة. الإيجار 35,000 جنيه في الشهر، تأمين شهرين.

أسئلة متكررة:
- الجراج: كل وحدات التجمع الخامس والشيخ زايد ليها جراج تحت الأرض بمكان عربية. شقة مدينتي ليها باركينج مفتوح قدام العمارة.
- الاستلام: شقة التجمع وشقة مدينتي استلام فوري. الدوبلكس والتاون هاوس استلام بعد سنة.
- الدفع: كاش أو تحويل بنكي أو شيكات للأقساط. مفيش تمويل عقاري من بنوك حالياً.
- الأمن: كل الكمبوندات فيها أمن 24 ساعة وكاميرات.
- الحيوانات الأليفة مسموحة في كل الوحدات.

خدمات الشركة:
- معاينة مجانية للوحدات بميعاد مسبق.
- مساعدة في إجراءات التسجيل والعقود.
- مفيش عمولة على المشتري في الوحدات الجديدة من المطور.

لحجز معاينة: العميل يبعت اسمه ورقمه والوحدة اللي عايزها، وفريق المبيعات هيكلمه في نفس اليوم.
""".strip()


async def main():
    await get_pool()
    existing = next((c for c in await list_companies() if c["name"] == NAME), None)
    if existing:
        await update_company_knowledge(existing["id"], KNOWLEDGE, WELCOME)
        company = await get_company_by_id(existing["id"])
        print("Updated demo client")
    else:
        await create_company(NAME, KNOWLEDGE, WELCOME)
        company = next(c for c in await list_companies() if c["name"] == NAME)
        print("Created demo client")
    print(f"company_id = {company['id']}")
    print(f"api_key    = {company['api_key']}")


if __name__ == "__main__":
    asyncio.run(main())
