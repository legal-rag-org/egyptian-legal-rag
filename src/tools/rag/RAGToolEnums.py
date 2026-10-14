from enum import Enum


class RAGToolEnums(Enum):
    NAME = "rag_search"

    DESCRIPTION = """
            "Search the Egyptian legal knowledge base across all supported legal domains. "
            "Supported domains include insurance and pensions, labour, tax, companies, "
            "civil service, customs, and reconciliation related to building violations "
            "(قانون التصالح في بعض مخالفات البناء). "
            "Use this tool for questions about Egyptian laws, regulations, legal rights, "
            "obligations, procedures, eligibility conditions, benefits, penalties, "
            "exemptions, fees, and other legal provisions. "
            "Use this tool whenever the user's question requires factual information "
            "from Egyptian laws or regulations."
        """