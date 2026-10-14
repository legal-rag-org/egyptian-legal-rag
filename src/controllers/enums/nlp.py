from enum import Enum


class NLPControllerEnums(Enum):

    NO_AVAILABLE_DOCUMENT_ANSWER = (
        "عذرًا، لا تتوفر في المستندات المتاحة معلومات كافية "
        "للإجابة عن هذا السؤال بدقة. "
        "يرجى إعادة صياغة السؤال أو تقديم مزيد من التفاصيل."
    )


    ALLOWED_METADATA_VALUES = {
        "law_number": {"148", "14", "91", "67", "81", "159", "207", "187"},
        "law_year": {"2019", "2025", "2005", "2016", "1981", "2020", "2023"},
        "domain" : {"insurance", "labour", "tax", "civil_service", "companies", "customs", "reconciliation"}
    }

    PORMPT_INJUCTED_ANSWER = "عذرًا، لا يمكنني معالجة هذا الطلب."

    FILTERABLE_METADATA = {
        "law_number",
        "law_year",
        "domain"
    }
